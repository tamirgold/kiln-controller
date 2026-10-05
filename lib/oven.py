import threading
import time
import datetime
import logging
import json
import config
import os
import digitalio
import busio
import adafruit_bitbangio as bitbangio
import statistics
import math
import tempfile
import subprocess
from lib.ramp_control import RampController

log = logging.getLogger(__name__)

class DupFilter(object):
    def __init__(self):
        self.msgs = set()

    def filter(self, record):
        rv = record.msg not in self.msgs
        self.msgs.add(record.msg)
        return rv

class Duplogger():
    def __init__(self):
        self.log = logging.getLogger("%s.dupfree" % (__name__))
        dup_filter = DupFilter()
        self.log.addFilter(dup_filter)
    def logref(self):
        return self.log

duplog = Duplogger().logref()

class Output(object):
    '''This represents a GPIO output that controls a solid
    state relay to turn the kiln elements on and off.
    inputs
        config.gpio_heat
        config.gpio_heat_invert
    '''
    def __init__(self):
        self.active = False
        self._heat_lock = threading.RLock()
        self._on_seconds = 0.0
        self._on_since = None
        self.heater = digitalio.DigitalInOut(config.gpio_heat) 
        self.off = config.gpio_heat_invert
        self.on = not self.off
        self.heater.switch_to_output(value=self.off)

    def heat(self,sleepfor):
        with self._heat_lock:
            self.heater.value = self.on
            self._on_since = time.monotonic()
        try:
            time.sleep(sleepfor)
        finally:
            self.cool(0)

    def cool(self,sleepfor):
        '''no active cooling, so sleep'''
        with self._heat_lock:
            self.heater.value = self.off
            if self._on_since is not None:
                self._on_seconds += max(0, time.monotonic() - self._on_since)
                self._on_since = None
        time.sleep(sleepfor)

    def seconds_on(self):
        with self._heat_lock:
            return self._on_seconds + (max(0, time.monotonic() - self._on_since)
                                       if self._on_since is not None else 0)

# wrapper for blinka board
class Board(object):
    '''This represents a blinka board where this code
    runs.
    '''
    def __init__(self):
        log.info("board: %s" % (self.name))
        self.temp_sensor.start()

class RealBoard(Board):
    '''Each board has a thermocouple board attached to it.
    Any blinka board that supports SPI can be used. The
    board is automatically detected by blinka.
    '''
    def __init__(self):
        self.name = None
        self.load_libs()
        self.temp_sensor = self.choose_tempsensor()
        Board.__init__(self) 

    def load_libs(self):
        import board
        self.name = board.board_id

    def choose_tempsensor(self):
        if config.max31855:
            return Max31855()
        if config.max31856:
            return Max31856()

class SimulatedBoard(Board):
    '''Simulated board used during simulations.
    See config.simulate
    '''
    def __init__(self):
        self.name = "simulated"
        self.temp_sensor = TempSensorSimulated()
        Board.__init__(self) 

class TempSensor(threading.Thread):
    '''Used by the Board class. Each Board must have
    a TempSensor.
    '''
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.time_step = config.sensor_time_wait
        self.status = ThermocoupleTracker()

class TempSensorSimulated(TempSensor):
    '''Simulates a temperature sensor '''
    def __init__(self):
        TempSensor.__init__(self)
        self.simulated_temperature = config.sim_t_env
    def temperature(self):
        return self.simulated_temperature

class TempSensorReal(TempSensor):
    '''real temperature sensor that takes many measurements
       during the time_step
       inputs
           config.temperature_average_samples 
    '''
    def __init__(self):
        TempSensor.__init__(self)
        self.sleeptime = self.time_step / float(config.temperature_average_samples)
        self.temptracker = TempTracker() 
        self.last_good_read = None
        self.last_error = None
        self.spi_setup()
        self.cs = digitalio.DigitalInOut(config.spi_cs)

    def spi_setup(self):
        if(hasattr(config,'spi_sclk') and
           hasattr(config,'spi_mosi') and
           hasattr(config,'spi_miso')):
            self.spi = bitbangio.SPI(config.spi_sclk, config.spi_mosi, config.spi_miso)
            log.info("Software SPI selected for reading thermocouple")
        else:
            import board
            self.spi = board.SPI();
            log.info("Hardware SPI selected for reading thermocouple")

    def get_temperature(self):
        '''read temp from tc and convert if needed'''
        try:
            temp = self.raw_temp() # raw_temp provided by subclasses
            if config.temp_scale.lower() == "f":
                temp = (temp*9/5)+32
            self.status.good()
            self.last_error = None
            return temp
        except ThermocoupleError as tce:
            if tce.ignore:
                log.error("Problem reading temp (ignored) %s" % (tce.message))
                self.status.good()
            else:
                if tce.message != self.last_error:
                    log.error("Problem reading temp %s" % (tce.message))
                    self.last_error = tce.message
                self.status.bad()
        return None

    def temperature(self):
        '''average temp over a duty cycle'''
        return self.temptracker.get_avg_temp()

    def cycle_temperature(self):
        '''Mean of the full sensor window for slow ramp-rate estimation.'''
        readings = self.temptracker.temps[:]
        return statistics.mean(readings) if readings else None

    def ready(self):
        return (self.last_good_read is not None and
                time.monotonic() - self.last_good_read <= self.time_step * 2 and
                len(self.temptracker.temps) >= self.temptracker.size and
                not self.status.over_error_limit())

    def run(self):
        while True:
            try:
                temp = self.get_temperature()
            except Exception:
                log.exception("Thermocouple read failed")
                self.status.bad()
                temp = None
            if temp is not None and math.isfinite(temp):
                self.temptracker.add(temp)
                self.last_good_read = time.monotonic()
            time.sleep(self.sleeptime)

class TempTracker(object):
    '''creates a sliding window of N temperatures per
       config.sensor_time_wait
    '''
    def __init__(self):
        self.size = config.temperature_average_samples
        self.temps = []
  
    def add(self,temp):
        self.temps.append(temp)
        while(len(self.temps) > self.size):
            del self.temps[0]

    def get_avg_temp(self, chop=25):
        '''
        take the median of the given values. this used to take an avg
        after getting rid of outliers. median works better.
        '''
        return statistics.median(self.temps) if self.temps else 0

class ThermocoupleTracker(object):
    '''Keeps sliding window to track successful/failed calls to get temp
       over the last two duty cycles.
    '''
    def __init__(self):
        self.size = config.temperature_average_samples * 2 
        self.status = [True for i in range(self.size)]
        self.limit = 30

    def good(self):
        '''True is good!'''
        self.status.append(True)
        del self.status[0]

    def bad(self):
        '''False is bad!'''
        self.status.append(False)
        del self.status[0]

    def error_percent(self):
        errors = sum(i == False for i in self.status) 
        return (errors/self.size)*100

    def over_error_limit(self):
        if self.error_percent() > self.limit:
            return True
        return False

class Max31855(TempSensorReal):
    '''each subclass expected to handle errors and get temperature'''
    def __init__(self):
        TempSensorReal.__init__(self)
        log.info("thermocouple MAX31855")
        import adafruit_max31855
        self.thermocouple = adafruit_max31855.MAX31855(self.spi, self.cs)

    def raw_temp(self):
        try:
            return self.thermocouple.temperature_NIST
        except RuntimeError as rte:
            if rte.args and rte.args[0]:
                raise Max31855_Error(rte.args[0])
            raise Max31855_Error('unknown')

class ThermocoupleError(Exception):
    '''
    thermocouple exception parent class to handle mapping of error messages
    and make them consistent across adafruit libraries. Also set whether
    each exception should be ignored based on settings in config.py.
    '''
    def __init__(self, message):
        self.ignore = False
        self.message = message
        self.map_message()
        self.set_ignore()
        super().__init__(self.message)

    def set_ignore(self):
        if self.message == "not connected" and config.ignore_tc_lost_connection == True:
            self.ignore = True
        if self.message == "short circuit" and config.ignore_tc_short_errors == True:
            self.ignore = True
        if self.message == "unknown" and config.ignore_tc_unknown_error == True:
            self.ignore = True
        if self.message == "cold junction range fault" and config.ignore_tc_cold_junction_range_error == True:
            self.ignore = True
        if self.message == "thermocouple range fault" and config.ignore_tc_range_error == True:
            self.ignore = True
        if self.message == "cold junction temp too high" and config.ignore_tc_cold_junction_temp_high == True:
            self.ignore = True
        if self.message == "cold junction temp too low" and config.ignore_tc_cold_junction_temp_low == True:
            self.ignore = True
        if self.message == "thermocouple temp too high" and config.ignore_tc_temp_high == True:
            self.ignore = True
        if self.message == "thermocouple temp too low" and config.ignore_tc_temp_low == True:
            self.ignore = True
        if self.message == "voltage too high or low" and config.ignore_tc_voltage_error == True:
            self.ignore = True

    def map_message(self):
        try:
            self.message = self.map[self.orig_message]
        except KeyError:
            self.message = "unknown"

class Max31855_Error(ThermocoupleError):
    '''
    All children must set self.orig_message and self.map
    '''
    def __init__(self, message):
        self.orig_message = message
        # this purposefully makes "fault reading" and
        # "Total thermoelectric voltage out of range..." unknown errors
        self.map = {
            "thermocouple not connected" : "not connected",
            "short circuit to ground" : "short circuit",
            "short circuit to power" : "short circuit",
            }
        super().__init__(message)

class Max31856_Error(ThermocoupleError):
    def __init__(self, message):
        self.orig_message = message
        self.map = {
            "cj_range" : "cold junction range fault",
            "tc_range" : "thermocouple range fault",
            "cj_high"  : "cold junction temp too high",
            "cj_low"   : "cold junction temp too low",
            "tc_high"  : "thermocouple temp too high",
            "tc_low"   : "thermocouple temp too low",
            "voltage"  : "voltage too high or low", 
            "open_tc"  : "not connected"
            }
        super().__init__(message)

class Max31856(TempSensorReal):
    '''each subclass expected to handle errors and get temperature'''
    def __init__(self):
        TempSensorReal.__init__(self)
        log.info("thermocouple MAX31856")
        import adafruit_max31856
        self.thermocouple = adafruit_max31856.MAX31856(self.spi,self.cs,
                                        thermocouple_type=config.thermocouple_type)
        if (config.ac_freq_50hz == True):
            self.thermocouple.noise_rejection = 50
        else:
            self.thermocouple.noise_rejection = 60

    def raw_temp(self):
        # The underlying adafruit library does not throw exceptions
        # for thermocouple errors. Instead, they are stored in 
        # dict named self.thermocouple.fault. Here we check that
        # dict for errors and raise an exception.
        # and raise Max31856_Error(message)
        temp = self.thermocouple.temperature
        for k,v in self.thermocouple.fault.items():
            if v:
                raise Max31856_Error(k)
        return temp

class Oven(threading.Thread):
    '''parent oven class. this has all the common code
       for either a real or simulated oven'''
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.temperature = 0
        self.time_step = config.sensor_time_wait
        self._restart_lock = threading.RLock()
        self.last_firing_energy = None
        self.reset()
        # Keep the final bill visible after a stopped/completed firing and reboot.
        try:
            with open(config.automatic_restart_state_file) as f:
                previous = json.load(f)
            if (isinstance(previous, dict) and previous.get('state') == 'IDLE' and previous.get('simulate') == config.simulate
                    and self.valid_energy(previous.get('last_firing_energy'))):
                self.last_firing_energy = previous['last_firing_energy']
        except (OSError, ValueError, TypeError):
            pass

    def reset(self):
        self.cost = 0
        self.energy_kwh = 0.0
        self.heater_on_seconds = 0.0
        self.energy_history_estimated = False
        self.energy_history_incomplete = False
        self.energy_tracking_started_at = time.time()
        self._simulated_on_seconds = 0.0
        self._energy_output_baseline = self.output.seconds_on() if hasattr(self, 'output') else 0.0
        self.state = "IDLE"
        self.profile = None
        self.start_time = 0
        self.runtime = 0
        self.run_started_at = None
        self.elapsed_origin_known = True
        self.totaltime = 0
        self.target = 0
        self.heat = 0
        self.heat_rate = 0
        self.heat_rate_temps = []
        self.pid = PID(ki=config.pid_ki, kd=config.pid_kd, kp=config.pid_kp)
        self.catching_up = False
        self.ramp_control = RampController()
        self._ramp_elapsed = 0.0

    @staticmethod
    def get_start_from_temperature(profile, temp):
        target_temp = profile.get_target_temperature(0)
        if temp > target_temp + 5:
            startat = profile.find_next_time_from_temperature(temp)
            log.info("seek_start is in effect, starting at: {} s, {} deg".format(round(startat), round(temp)))
        else:
            startat = 0
        return startat

    def set_heat_rate(self,runtime,temp):
        '''heat rate is the heating rate in degrees/hour
        '''
        # arbitrary number of samples
        # the time this covers changes based on a few things
        numtemps = 60
        if self.heat_rate_temps and runtime - self.heat_rate_temps[-1][0] < 1:
            return
        self.heat_rate_temps.append((runtime,temp))
         
        # drop old temps off the list
        if len(self.heat_rate_temps) > numtemps:
            self.heat_rate_temps = self.heat_rate_temps[-1*numtemps:]
        time2 = self.heat_rate_temps[-1][0]
        time1 = self.heat_rate_temps[0][0]
        temp2 = self.heat_rate_temps[-1][1]
        temp1 = self.heat_rate_temps[0][1]
        if time2 - time1 >= 10:
            self.heat_rate = ((temp2 - temp1) / (time2 - time1))*3600

    def record_history(self, force=False, finish=None):
        history = getattr(self, 'firing_history', None)
        if history is None:
            return
        with self._restart_lock:
            try:
                history_state = self.get_state()
                if not self.pid.pidstats or self.runtime >= self.totaltime:
                    history_state['target'] = None
                history.capture(history_state, force=force, finish=finish)
            except (OSError, ValueError) as exc:
                history.error = 'Firing history could not be saved: ' + str(exc)
                log.exception('Could not save firing history')

    def run_profile(self, profile, startat=0, allow_seek=True, recovery=None):
        with self._restart_lock:
            if self.state in ('RUNNING', 'PAUSED'):
                self.record_history(force=True, finish='replaced')
            self._run_profile(profile, startat, allow_seek)
            if recovery is not None:
                origin = recovery.get('run_started_at')
                if isinstance(origin, (int, float)) and math.isfinite(origin) and 0 < origin <= time.time():
                    self.run_started_at = origin
                    self.elapsed_origin_known = recovery.get('elapsed_origin_known', True)
                else:
                    self.elapsed_origin_known = False
                self.restore_energy(recovery)
            self.record_history(force=True)

    def _run_profile(self, profile, startat=0, allow_seek=True):
        log.debug('run_profile run on thread' + threading.current_thread().name)
        runtime = startat * 60
        if allow_seek:
            if self.state == 'IDLE':
                if config.seek_start:
                    temp = self.board.temp_sensor.temperature()  # Defined in a subclass
                    runtime += self.get_start_from_temperature(profile, temp)

        self.reset()
        self.startat = startat * 60
        self.runtime = runtime
        self.start_time = self.get_start_time()
        self.profile = profile
        self.totaltime = profile.get_duration()
        self.update_target_temp()
        self.run_started_at = time.time()
        self.state = "RUNNING"
        log.info("Running schedule %s starting at %d minutes" % (profile.name,startat))
        log.info("Starting")

    def abort_run(self, reason="stopped"):
        with self._restart_lock:
            if hasattr(self, 'output'):
                self.output.cool(0)
            if self.state in ('RUNNING', 'PAUSED'):
                self.update_cost()
                self.record_history(force=True, finish=reason)
                self.last_firing_energy = dict(self.energy_state(), profile=self.profile.name if self.profile else None,
                                               finished_at=time.time())
            self.reset()
            self.save_automatic_restart_state()

    def get_start_time(self):
        return datetime.datetime.now() - datetime.timedelta(milliseconds = self.runtime * 1000)

    def kiln_must_catch_up(self):
        '''shift the whole schedule forward in time by one time_step
        when temperature is behind the current ramp, or outside a hold'''
        self.catching_up = False
        if not config.kiln_must_catch_up or self.profile is None:
            return
        previous, following = self.profile.get_surrounding_points(self.runtime)
        if previous is None or following is None or following[0] <= previous[0]:
            # Let the normal lifecycle handle an absent/completed segment.
            return

        temp = self.board.temp_sensor.temperature() + config.thermocouple_offset
        direction = following[1] - previous[1]
        tolerance = getattr(config, 'catch_up_tolerance', 0) or config.pid_control_window
        too_cold = self.target - temp > tolerance
        too_hot = temp - self.target > tolerance
        # An upward ramp can catch up with an overshoot by advancing its
        # target. PID still switches heat off when temperature is too high.
        # Holds wait on both sides; cooling ramps wait only when too hot.
        if (direction >= 0 and too_cold) or (direction <= 0 and too_hot):
            log.info("kiln must catch up, %s, shifting schedule", "too cold" if too_cold else "too hot")
            self.start_time = self.get_start_time()
            self.catching_up = True

    def update_runtime(self):

        runtime_delta = datetime.datetime.now() - self.start_time
        if runtime_delta.total_seconds() < 0:
            runtime_delta = datetime.timedelta(0)

        self.runtime = runtime_delta.total_seconds()

    def update_target_temp(self):
        self.target = self.profile.get_target_temperature(self.runtime)

    def controlled_heat_duty(self, pid_now, elapsed_now):
        """Run the existing temperature PID, then bounded slow rate feedback."""
        sensor = self.board.temp_sensor
        temperature = sensor.temperature() + config.thermocouple_offset
        integral_before = self.pid.iterm
        base = self.pid.compute(self.target, temperature, pid_now)
        rate_temperature = sensor.cycle_temperature() if hasattr(sensor, 'cycle_temperature') else temperature
        if rate_temperature is not None and hasattr(sensor, 'cycle_temperature'):
            rate_temperature += config.thermocouple_offset
        previous, following = self.profile.get_surrounding_points(self.runtime) if self.profile else (None, None)
        segment = (*previous, *following) if previous is not None and following is not None else None
        enabled = getattr(config, 'automatic_ramp_control', False)
        maximum = 1.0
        if config.throttle_below_temp and config.throttle_percent and self.target <= config.throttle_below_temp:
            # Preserve existing PID behavior inside its window, while never
            # allowing the new correction to exceed the low-temperature cap.
            maximum = max(base, config.throttle_percent / 100)
        output = self.ramp_control.update(now=elapsed_now, temperature=rate_temperature,
            control_temperature=temperature, target=self.target, segment=segment,
            pid_output=base, enabled=enabled, state=self.state,
            sensor_ready=config.simulate or sensor.ready(),
            tolerance=getattr(config, 'catch_up_tolerance', 0) or config.pid_control_window,
            control_window=config.pid_control_window, max_output=maximum,
            scale=1.8 if config.temp_scale.lower() == 'f' else 1.0)
        report = self.ramp_control.snapshot()
        # Preserve the existing PID integration unless the added rate trim
        # causes saturation. Do not retune baseline PID behavior implicitly.
        integral_delta = self.pid.iterm - integral_before
        held = (enabled and report['phase'] in ('heating', 'cooling') and
                ((output >= maximum - 1e-9 and output > base + 1e-9 and integral_delta > 0) or
                 (output <= 1e-9 and output < base - 1e-9 and integral_delta < 0)))
        if held:
            self.pid.iterm = integral_before
            self.pid.pidstats['i'] = integral_before
        self.pid.pidstats.update(base_out=base, out=output,
                                 ramp_trim=report['applied_trim_percent'], integral_held=held)
        if enabled and report['status'] == 'correcting':
            log.info('ramp control: requested=%.2f/h measured=%.2f/h adjustment=%+.2f%% output=%.2f%%',
                     report['requested_rate'], report['measured_rate'], report['applied_trim_percent'], output * 100)
        return output

    def reset_if_emergency(self):
        '''reset if the temperature is way TOO HOT, or other critical errors detected'''
        if (self.board.temp_sensor.temperature() + config.thermocouple_offset >=
            config.emergency_shutoff_temp):
            log.info("emergency!!! temperature too high")
            if config.ignore_temp_too_high == False:
                self.abort_run("over_temperature")
        
        if self.board.temp_sensor.status.over_error_limit():
            log.info("emergency!!! too many errors in a short period")
            if config.ignore_tc_too_many_errors == False:
                self.abort_run("sensor_fault")

    def reset_if_schedule_ended(self):
        if self.runtime > self.totaltime:
            log.info("schedule ended, shutting down")
            log.info("total cost = %s%.2f" % (config.currency_type,self.cost))
            self.abort_run("completed")

    def update_cost(self):
        # The output counter includes a pulse in progress and excludes all
        # off-time. Sampling twice (e.g. two browsers) cannot double-charge.
        with self._restart_lock:
            total = self.output.seconds_on() if hasattr(self, 'output') else self._simulated_on_seconds
            seconds = max(0.0, total - self._energy_output_baseline)
            self._energy_output_baseline = total
            if self.state in ('RUNNING', 'PAUSED'):
                self.heater_on_seconds += seconds
                energy = config.kw_elements * seconds / 3600.0
                self.energy_kwh += energy
                self.cost += energy * config.kwh_rate

    def energy_state(self):
        return dict(version=1, heater_on_seconds=self.heater_on_seconds,
                    energy_kwh=self.energy_kwh, cost=self.cost,
                    currency_type=config.currency_type,
                    kw_elements=config.kw_elements, kwh_rate=config.kwh_rate,
                    history_estimated=self.energy_history_estimated,
                    history_incomplete=self.energy_history_incomplete,
                    tracking_started_at=self.energy_tracking_started_at)

    @staticmethod
    def valid_energy(value):
        return (isinstance(value, dict) and value.get('version') == 1 and
                all(isinstance(value.get(k), (int, float)) and not isinstance(value[k], bool)
                    and math.isfinite(value[k]) and value[k] >= 0
                    for k in ('heater_on_seconds', 'energy_kwh', 'cost', 'tracking_started_at')) and
                isinstance(value.get('currency_type'), str))

    def restore_energy(self, saved):
        energy = saved.get('energy_accounting')
        if self.valid_energy(energy):
            self.heater_on_seconds = energy['heater_on_seconds']
            self.energy_kwh = energy['energy_kwh']
            # Revalue at the configured tariff only if the currency changed.
            self.cost = (energy['cost'] if energy['currency_type'] == config.currency_type
                         else self.energy_kwh * config.kwh_rate)
            self.energy_history_estimated = bool(energy.get('history_estimated'))
            self.energy_history_incomplete = bool(energy.get('history_incomplete'))
            self.energy_tracking_started_at = energy['tracking_started_at']
        else:
            # Old cost values counted pulses incorrectly and cannot be used.
            self.energy_history_incomplete = True

    def get_state(self):
        self.update_cost()
        temp = 0
        try:
            temp = self.board.temp_sensor.temperature() + config.thermocouple_offset
        except AttributeError as error:
            # this happens at start-up with a simulated oven
            temp = 0
            pass

        sensor_ready = config.simulate or self.board.temp_sensor.ready()
        if sensor_ready:
            self.set_heat_rate(time.monotonic(), temp)
        else:
            self.heat_rate_temps = []
            self.heat_rate = 0
        timestamp = time.time()

        state = {
            'cost': self.cost,
            'energy_accounting': self.energy_state(),
            'last_firing_energy': self.last_firing_energy,
            'runtime': self.runtime,
            'temperature': temp,
            'target': self.target,
            'state': self.state,
            'heat': self.heat,
            'heat_rate': self.heat_rate,
            'totaltime': self.totaltime,
            'kwh_rate': config.kwh_rate,
            'currency_type': config.currency_type,
            'profile': self.profile.name if self.profile else None,
            'profile_data': {'name': self.profile.name, 'data': self.profile.data} if self.profile else None,
            'pidstats': self.pid.pidstats,
            'ramp_control': self.ramp_control.snapshot(),
            'catching_up': self.catching_up,
            'sensor_ready': sensor_ready,
            'simulate': config.simulate,
            'timestamp': timestamp,
            'run_started_at': self.run_started_at,
            'elapsed_seconds': max(0, timestamp - self.run_started_at) if self.run_started_at else 0,
            'elapsed_origin_known': self.elapsed_origin_known,
            'heat_rate_ready': bool(len(self.heat_rate_temps) > 1 and
                                    self.heat_rate_temps[-1][0] - self.heat_rate_temps[0][0] >= 10),
            'kw_elements': config.kw_elements,
            'history_error': getattr(getattr(self, 'firing_history', None), 'error', None),
        }
        return state

    def save_state(self):
        # A power cut must leave either the previous complete state or the
        # new complete state, never a truncated JSON file.
        path = config.automatic_restart_state_file
        directory = os.path.dirname(os.path.abspath(path))
        with self._restart_lock:
            state = self.get_state()
            state['saved_at'] = time.time()
            state['temp_scale'] = config.temp_scale
            state['simulate'] = config.simulate
            if self.profile:
                state['profile_data'] = {'name': self.profile.name,
                                         'data': self.profile.data}
            fd, temporary = tempfile.mkstemp(prefix='.kiln-state-', dir=directory)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=4, allow_nan=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, path)
                directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def state_file_is_old(self):
        '''returns True is state files is older than 15 mins default
                   False if younger
                   True if state file cannot be opened or does not exist
        '''
        if os.path.isfile(config.automatic_restart_state_file):
            state_age = os.path.getmtime(config.automatic_restart_state_file)
            now = time.time()
            minutes = (now - state_age)/60
            if(0 <= minutes <= config.automatic_restart_window):
                return False
        return True

    def save_automatic_restart_state(self):
        # only save state if the feature is enabled
        if not config.automatic_restarts == True:
            return False
        self.save_state()

    def should_i_automatic_restart(self):
        # only automatic restart if the feature is enabled
        if not config.automatic_restarts == True:
            return False
        if self.state_file_is_old():
            duplog.info("automatic restart not possible. state file does not exist or is too old.")
            return False

        try:
            with open(config.automatic_restart_state_file) as infile:
                d = json.load(infile)
            age = time.time() - d['saved_at']
            if (d['state'] != 'RUNNING' or
                    d['temp_scale'] != config.temp_scale or
                    d['simulate'] != config.simulate or
                    not 0 <= age <= config.automatic_restart_window * 60):
                return False
            if not all(isinstance(d[k], (int, float)) and not isinstance(d[k], bool)
                       and math.isfinite(d[k]) and d[k] >= 0
                       for k in ('runtime', 'cost')):
                return False
            profile = Profile(json.dumps(d['profile_data']))
            if (profile.name != d['profile'] or len(profile.data) < 2 or
                    profile.data[0][0] != 0 or
                    not all(math.isfinite(t) and math.isfinite(v)
                            for t, v in profile.data) or
                    any(b[0] <= a[0] for a, b in zip(profile.data, profile.data[1:])) or
                    not 0 <= d['runtime'] < profile.get_duration()):
                return False
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            duplog.error('Invalid restart state; leaving kiln idle.')
            return False
        return True

    def automatic_restart(self):
        if not self.should_i_automatic_restart():
            return
        if not config.simulate and getattr(config, 'require_synced_clock_for_restart', False):
            try:
                sync = subprocess.run(['/usr/bin/chronyc', 'waitsync', '1'],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      timeout=3)
                if sync.returncode != 0:
                    return
            except (OSError, subprocess.TimeoutExpired):
                return
        # Leave saved progress intact while waiting for valid sensor data.
        if not config.simulate and not self.board.temp_sensor.ready():
            return
        with open(config.automatic_restart_state_file) as infile: d = json.load(infile)
        startat = d["runtime"]/60
        log.info("automatically restarting profile = %s at minute = %s", d['profile'], startat)
        profile = Profile(json.dumps(d['profile_data']))
        self.run_profile(profile, startat=startat, allow_seek=False, recovery=d)
        if hasattr(self, 'ovenwatcher'):
            self.ovenwatcher.record(profile)

    def set_ovenwatcher(self,watcher):
        log.info("ovenwatcher set in oven class")
        self.ovenwatcher = watcher

    def run(self):
        while True:
            log.debug('Oven running on ' + threading.current_thread().name)
            if self.state == "IDLE":
                if self.should_i_automatic_restart() == True:
                    self.automatic_restart()
                time.sleep(1)
                continue
            if self.state == "PAUSED":
                self.save_automatic_restart_state()
                self.start_time = self.get_start_time()
                self.update_runtime()
                self.update_target_temp()
                self.heat_then_cool()
                self.reset_if_emergency()
                self.reset_if_schedule_ended()
                continue
            if self.state == "RUNNING":
                self.save_automatic_restart_state()
                self.kiln_must_catch_up()
                self.update_runtime()
                self.update_target_temp()
                self.heat_then_cool()
                self.reset_if_emergency()
                self.reset_if_schedule_ended()

class SimulatedOven(Oven):

    def __init__(self):
        self.board = SimulatedBoard()
        self.t_env = config.sim_t_env
        self.c_heat = config.sim_c_heat
        self.c_oven = config.sim_c_oven
        self.p_heat = config.sim_p_heat
        self.R_o_nocool = config.sim_R_o_nocool
        self.R_ho_noair = config.sim_R_ho_noair
        self.R_ho = self.R_ho_noair
        self.speedup_factor = config.sim_speedup_factor

        # set temps to the temp of the surrounding environment
        self.t = config.sim_t_env  # deg C or F temp of oven
        self.t_h = self.t_env #deg C temp of heating element

        super().__init__()

        self.start_time = self.get_start_time();

        # start thread
        self.start()
        log.info("SimulatedOven started")

    # runtime is in sped up time, start_time is actual time of day
    def get_start_time(self):
        return datetime.datetime.now() - datetime.timedelta(milliseconds = self.runtime * 1000 / self.speedup_factor)

    def update_runtime(self):
        runtime_delta = datetime.datetime.now() - self.start_time
        if runtime_delta.total_seconds() < 0:
            runtime_delta = datetime.timedelta(0)

        self.runtime = runtime_delta.total_seconds() * self.speedup_factor

    def update_target_temp(self):
        self.target = self.profile.get_target_temperature(self.runtime)

    def heating_energy(self,pid):
        # using pid here simulates the element being on for
        # only part of the time_step
        self.Q_h = self.p_heat * self.time_step * pid

    def temp_changes(self):
        #temperature change of heat element by heating
        self.t_h += self.Q_h / self.c_heat

        #energy flux heat_el -> oven
        self.p_ho = (self.t_h - self.t) / self.R_ho

        #temperature change of oven and heating element
        self.t += self.p_ho * self.time_step / self.c_oven
        self.t_h -= self.p_ho * self.time_step / self.c_heat

        #temperature change of oven by cooling to environment
        self.p_env = (self.t - self.t_env) / self.R_o_nocool
        self.t -= self.p_env * self.time_step / self.c_oven
        self.temperature = self.t
        self.board.temp_sensor.simulated_temperature = self.t

    def heat_then_cool(self):
        now_simulator = self.start_time + datetime.timedelta(milliseconds = self.runtime * 1000)
        pid = self.controlled_heat_duty(now_simulator, self._ramp_elapsed)
        self._ramp_elapsed += self.time_step

        heat_on = float(self.time_step * pid)
        heat_off = float(self.time_step * (1 - pid))

        self.heating_energy(pid)
        self.temp_changes()

        # self.heat is for the front end to display if the heat is on
        self.heat = 0.0
        if heat_on > 0:
            self.heat = heat_on

        log.info("simulation: -> %dW heater: %.0f -> %dW oven: %.0f -> %dW env" % (int(self.p_heat * pid),
            self.t_h,
            int(self.p_ho),
            self.t,
            int(self.p_env)))

        time_left = self.totaltime - self.runtime

        try:
            log.info("temp=%.2f, target=%.2f, error=%.2f, pid=%.2f, p=%.2f, i=%.2f, d=%.2f, heat_on=%.2f, heat_off=%.2f, run_time=%d, total_time=%d, time_left=%d" %
                (self.pid.pidstats['ispoint'],
                self.pid.pidstats['setpoint'],
                self.pid.pidstats['err'],
                self.pid.pidstats['pid'],
                self.pid.pidstats['p'],
                self.pid.pidstats['i'],
                self.pid.pidstats['d'],
                heat_on,
                heat_off,
                self.runtime,
                self.totaltime,
                time_left))
        except KeyError:
            pass

        # we don't actually spend time heating & cooling during
        # a simulation, so sleep.
        time.sleep(self.time_step / self.speedup_factor)
        self._simulated_on_seconds += heat_on
        self.update_cost()


class RealOven(Oven):

    def __init__(self):
        self.board = RealBoard()
        self.output = Output()

        # call parent init
        Oven.__init__(self)

        # start thread
        self.start()

    def reset(self):
        self.output.cool(0)
        super().reset()

    def heat_then_cool(self):
        # A missing, failed, or stale thermocouple must never enable heat,
        # including the first cycle after automatic recovery.
        if (self.state not in ('RUNNING', 'PAUSED') or
                not self.board.temp_sensor.ready()):
            self.output.cool(0)
            self.abort_run("sensor_fault")
            time.sleep(self.time_step)
            return
        self.reset_if_emergency()
        if self.state == 'IDLE':
            return
        pid = self.controlled_heat_duty(datetime.datetime.now(), time.monotonic())

        heat_on = float(self.time_step * pid)
        heat_off = float(self.time_step * (1 - pid))

        # self.heat is for the front end to display if the heat is on
        self.heat = 0.0
        if heat_on > 0:
            self.heat = 1.0

        if heat_on:
            self.output.heat(heat_on)
        if heat_off:
            self.output.cool(heat_off)
        time_left = self.totaltime - self.runtime
        try:
            log.info("temp=%.2f, target=%.2f, error=%.2f, pid=%.2f, p=%.2f, i=%.2f, d=%.2f, heat_on=%.2f, heat_off=%.2f, run_time=%d, total_time=%d, time_left=%d" %
                (self.pid.pidstats['ispoint'],
                self.pid.pidstats['setpoint'],
                self.pid.pidstats['err'],
                self.pid.pidstats['pid'],
                self.pid.pidstats['p'],
                self.pid.pidstats['i'],
                self.pid.pidstats['d'],
                heat_on,
                heat_off,
                self.runtime,
                self.totaltime,
                time_left))
        except KeyError:
            pass

class Profile():
    def __init__(self, json_data):
        obj = json.loads(json_data)
        self.name = obj["name"]
        self.data = sorted(obj["data"])

    def get_duration(self):
        return max([t for (t, x) in self.data])

    #  x = (y-y1)(x2-x1)/(y2-y1) + x1
    @staticmethod
    def find_x_given_y_on_line_from_two_points(y, point1, point2):
        if point1[0] > point2[0]: return 0  # time2 before time1 makes no sense in kiln segment
        if point1[1] >= point2[1]: return 0 # Zero will crach. Negative temeporature slope, we don't want to seek a time.
        x = (y - point1[1]) * (point2[0] -point1[0] ) / (point2[1] - point1[1]) + point1[0]
        return x

    def find_next_time_from_temperature(self, temperature):
        time = 0 # The seek function will not do anything if this returns zero, no useful intersection was found
        for index, point2 in enumerate(self.data):
            if point2[1] >= temperature:
                if index > 0: #  Zero here would be before the first segment
                    if self.data[index - 1][1] <= temperature: # We have an intersection
                        time = self.find_x_given_y_on_line_from_two_points(temperature, self.data[index - 1], point2)
                        if time == 0:
                            if self.data[index - 1][1] == point2[1]: # It's a flat segment that matches the temperature
                                time = self.data[index - 1][0]
                                break

        return time

    def get_surrounding_points(self, time):
        if time > self.get_duration():
            return (None, None)

        prev_point = None
        next_point = None

        for i in range(len(self.data)):
            if time < self.data[i][0]:
                prev_point = self.data[i-1]
                next_point = self.data[i]
                break

        return (prev_point, next_point)

    def get_target_temperature(self, time):
        if time >= self.get_duration():
            return 0

        (prev_point, next_point) = self.get_surrounding_points(time)

        incl = float(next_point[1] - prev_point[1]) / float(next_point[0] - prev_point[0])
        temp = prev_point[1] + (time - prev_point[0]) * incl
        return temp


class PID():

    def __init__(self, ki=1, kp=1, kd=1):
        self.ki = ki
        self.kp = kp
        self.kd = kd
        self.lastNow = datetime.datetime.now()
        self.iterm = 0
        self.lastErr = 0
        self.pidstats = {}

    # FIX - this was using a really small window where the PID control
    # takes effect from -1 to 1. I changed this to various numbers and
    # settled on -50 to 50 and then divide by 50 at the end. This results
    # in a larger PID control window and much more accurate control...
    # instead of what used to be binary on/off control.
    def compute(self, setpoint, ispoint, now):
        timeDelta = (now - self.lastNow).total_seconds()

        window_size = 100

        error = float(setpoint - ispoint)

        # this removes the need for config.stop_integral_windup
        # it turns the controller into a binary on/off switch
        # any time it's outside the window defined by
        # config.pid_control_window
        icomp = 0
        output = 0
        out4logs = 0
        dErr = 0
        if error < (-1 * config.pid_control_window):
            log.info("kiln outside pid control window, max cooling")
            output = 0
            # it is possible to set self.iterm=0 here and also below
            # but I dont think its needed
        elif error > (1 * config.pid_control_window):
            log.info("kiln outside pid control window, max heating")
            output = 1
            if config.throttle_below_temp and config.throttle_percent:
                if setpoint <= config.throttle_below_temp:
                    output = config.throttle_percent/100
                    log.info("max heating throttled at %d percent below %d degrees to prevent overshoot" % (config.throttle_percent,config.throttle_below_temp))
        else:
            icomp = (error * timeDelta * (1/self.ki))
            self.iterm += (error * timeDelta * (1/self.ki))
            dErr = (error - self.lastErr) / timeDelta
            output = self.kp * error + self.iterm + self.kd * dErr
            output = sorted([-1 * window_size, output, window_size])[1]
            out4logs = output
            output = float(output / window_size)
            
        self.lastErr = error
        self.lastNow = now

        # no active cooling
        if output < 0:
            output = 0

        self.pidstats = {
            'time': time.mktime(now.timetuple()),
            'timeDelta': timeDelta,
            'setpoint': setpoint,
            'ispoint': ispoint,
            'err': error,
            'errDelta': dErr,
            'p': self.kp * error,
            'i': self.iterm,
            'd': self.kd * dErr,
            'kp': self.kp,
            'ki': self.ki,
            'kd': self.kd,
            'pid': out4logs,
            'out': output,
        }

        return output
