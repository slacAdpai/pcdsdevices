"""
Module for the various spectrometers.
"""
from ophyd.device import Component as Cpt
from ophyd.device import Device
from ophyd.device import FormattedComponent as FCpt

from .epics_motor import BeckhoffAxis
from .interface import BaseInterface, LightpathMixin
from .signal import InternalSignal


class Kmono(Device, BaseInterface, LightpathMixin):
    """
    K-edge Monochromator: Used for Undulator tuning and other experiments.

    This device has 3 main members: the crystal (xtal), the reticle
    (ret), and the diode (diode).

    The crystal angle motion has a pitch of 1000:1 HD of 0.6 mm. The crystal
    angle motor has 1000 steps. The crystal vertical motor moves the in and
    out of the beam path.

    The reticle horizontal motor allows for adjustments in the +/- x direction.
    The reticle vertical motor moves reticle in and out of the beam path in
    the +/- y direction.

    The diode horizontal motor allows for adjustments in the +/- x direction.
    The diode vertical motor moves reticle in and out of the beam path in
    the +/- y direction.
    """

    tab_component_names = True

    _icon = 'fa.diamond'
    lightpath_cpts = ['xtal_in', 'xtal_out',
                      'ret_in', 'ret_out',
                      'diode_in', 'diode_out']

    xtal_angle = Cpt(BeckhoffAxis, ':XTAL_ANGLE', kind='normal')
    xtal_vert = Cpt(BeckhoffAxis, ':XTAL_VERT', kind='normal')
    ret_horiz = Cpt(BeckhoffAxis, ':RET_HORIZ', kind='normal')
    ret_vert = Cpt(BeckhoffAxis, ':RET_VERT', kind='normal')
    diode_horiz = Cpt(BeckhoffAxis, ':DIODE_HORIZ', kind='normal')
    diode_vert = Cpt(BeckhoffAxis, ':DIODE_VERT', kind='normal')

    xtal_in = Cpt(InternalSignal, value=None, kind='omitted')
    xtal_out = Cpt(InternalSignal, value=None, kind='omitted')
    ret_in = Cpt(InternalSignal, value=None, kind='omitted')
    ret_out = Cpt(InternalSignal, value=None, kind='omitted')
    diode_in = Cpt(InternalSignal, value=None, kind='omitted')
    diode_out = Cpt(InternalSignal, value=None, kind='omitted')

    def _update_if_changed(self, value, signal):
        if value != signal.get():
            signal.put(value, force=True)

    def _update_state(self, inserted, removed, state):
        self._update_if_changed(inserted, getattr(self, state + '_in'))
        self._update_if_changed(removed, getattr(self, state + '_out'))

    @xtal_vert.sub_default
    def _xtal_state(self, *args, value, **kwargs):
        if value is not None:
            inserted = value > 50
            removed = value < 2
            self._update_state(inserted, removed, 'xtal')

    @ret_vert.sub_default
    def _ret_state(self, *args, value, **kwargs):
        if value is not None:
            inserted = value < 0
            removed = not inserted
            self._update_state(inserted, removed, 'ret')

    @diode_vert.sub_default
    def _diode_state(self, *args, value, **kwargs):
        if value is not None:
            inserted = value < 2
            removed = value > 96.5
            self._update_state(inserted, removed, 'diode')

    def _set_lightpath_states(self, lightpath_values):
        xtal_in = lightpath_values[self.xtal_in]['value']
        xtal_out = lightpath_values[self.xtal_out]['value']
        ret_in = lightpath_values[self.ret_in]['value']
        ret_out = lightpath_values[self.ret_out]['value']
        diode_in = lightpath_values[self.diode_in]['value']
        diode_out = lightpath_values[self.diode_out]['value']

        self._inserted = any((xtal_in, ret_in, diode_in))
        self._removed = all((xtal_out, ret_out, diode_out))

        if ret_in:
            self._transmission = 0
        else:
            self._transmission = 1


class VonHamosCrystal(Device, BaseInterface):
    """Pitch, yaw, and translation motors for control of a single crystal."""
    tab_component_names = True

    pitch = Cpt(BeckhoffAxis, ':Pitch', kind='normal')
    yaw = Cpt(BeckhoffAxis, ':Yaw', kind='normal')
    trans = Cpt(BeckhoffAxis, ':Translation', kind='normal')


class VonHamosFE(Device, BaseInterface):
    """
    von Hamos spectrometer with Focus and Energy motors.

    These motors should be run as user stages and have their PVs passed into
    this object as keyword arguments, as labeled.

    Parameters
    ----------
    prefix : str, optional
        von Hamos base PV.

    name : str
        A name to refer to the device.

    prefix_focus : str
        The EPICS base PV of the motor controlling the spectrometer's focus.

    prefix_energy : str
        The EPICS base PV of the motor controlling the spectrometer energy.
    """

    tab_component_names = True

    # Update PVs in IOC and change here to reflect
    f = FCpt(BeckhoffAxis, '{self._prefix_focus}', kind='normal')
    e = FCpt(BeckhoffAxis, '{self._prefix_energy}', kind='normal')

    def __init__(self, *args, name, prefix_focus, prefix_energy, **kwargs):
        self._prefix_focus = prefix_focus
        self._prefix_energy = prefix_energy
        if args:
            super().__init__(args[0], name=name, **kwargs)
        else:
            super().__init__('', name=name, **kwargs)


class VonHamosFER(VonHamosFE):
    """
    von Hamos spectrometer with Focus, Energy, and Rotation motors.

    These motors should be run as user stages and have their PVs passed into
    this object as keyword arguments, as labeled.

    Parameters
    ----------
    prefix : str, optional
        von Hamos base PV.

    name : str
        A name to refer to the device.

    prefix_focus : str
        The EPICS base PV of the motor controlling the spectrometer's focus.

    prefix_energy : str
        The EPICS base PV of the motor controlling the spectrometer energy.

    prefix_rot : str
        The EPICS base PV of the common rotation motor.
    """

    rot = FCpt(BeckhoffAxis, '{self._prefix_rot}', kind='normal')

    def __init__(self, *args, name, prefix_rot, **kwargs):
        self._prefix_rot = prefix_rot
        if args:
            super().__init__(args[0], name=name, **kwargs)
        else:
            super().__init__('', name=name, **kwargs)


class VonHamos4Crystal(VonHamosFE):
    """
    von Hamos spectrometer with four crystals and focus and energy motors.

    The common motors should be run as user stages and have their PVs passed
    into this object as keyword arguments. The crystal motors should be run
    from a Beckhoff IOC and their PVs will be inferred from the base prefix.

    Parameters
    ----------
    prefix : str
        von Hamos base PV.

    name : str
        A name to refer to the device.

    prefix_focus : str
        The EPICS base PV of the motor controlling the spectrometer's focus.

    prefix_energy : str
        The EPICS base PV of the motor controlling the spectrometer energy.
    """

    c1 = Cpt(VonHamosCrystal, ':1', kind='normal')
    c2 = Cpt(VonHamosCrystal, ':2', kind='normal')
    c3 = Cpt(VonHamosCrystal, ':3', kind='normal')
    c4 = Cpt(VonHamosCrystal, ':4', kind='normal')

    def __init__(self, prefix, *, name, **kwargs):
        super().__init__(prefix, name=name, **kwargs)
