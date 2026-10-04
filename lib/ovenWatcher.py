import threading,logging,json,time,datetime
from oven import Oven
log = logging.getLogger(__name__)

class OvenWatcher(threading.Thread):
    def __init__(self,oven):
        self.last_profile = None
        self.last_log = []
        self.started = None
        self.recording = False
        self.observers = []
        threading.Thread.__init__(self)
        self.daemon = True
        self.oven = oven
        self.start()

    def run(self):
        while True:
            with self.oven._restart_lock:
                oven_state = self.oven.get_state()
                self.oven.record_history()
                history = getattr(self.oven, 'firing_history', None)
                if history and self.oven.state == 'IDLE' and not self.oven.should_i_automatic_restart():
                    try:
                        history.reconcile_idle()
                    except (OSError, ValueError) as exc:
                        history.error = 'Firing summary could not be saved: ' + str(exc)
                        log.exception('Could not finish history record')
           
            # record state for any new clients that join
            if oven_state.get("state") in ("RUNNING", "PAUSED"):
                self.last_log.append(oven_state)
                if len(self.last_log) > 4000:
                    self.last_log = self.last_log[:-1:2] + [self.last_log[-1]]
            else:
                self.recording = False
            self.notify_all(oven_state)
            # Keep UI status and durable history responsive even with a slow relay cycle.
            time.sleep(min(2.0, self.oven.time_step))

    def lastlog_subset(self,maxpts=300):
        '''send about maxpts from lastlog by skipping unwanted data'''
        totalpts = len(self.last_log)
        if (totalpts <= maxpts):
            return self.last_log
        return [self.last_log[round(i * (totalpts - 1) / (maxpts - 1))]
                for i in range(maxpts)]

    def record(self, profile):
        self.last_profile = profile
        self.last_log = []
        self.started = datetime.datetime.now()
        self.recording = True
        #we just turned on, add first state for nice graph
        self.last_log.append(self.oven.get_state())

    def add_observer(self,observer):
        if self.last_profile:
            p = {
                "name": self.last_profile.name,
                "data": self.last_profile.data, 
                "type" : "profile"
            }
        else:
            p = None
        
        backlog = {
            'type': "backlog",
            'profile': p,
            'log': self.lastlog_subset(),
            #'started': self.started
        }
        backlog_json = json.dumps(backlog)
        try:
            observer.send(backlog_json)
        except:
            log.error("Could not send backlog to new observer")
        
        self.observers.append(observer)

    def notify_all(self,message):
        message_json = json.dumps(message)
        log.debug("sending to %d clients: %s"%(len(self.observers),message_json))

        for wsock in self.observers:
            if wsock:
                try:
                    wsock.send(message_json)
                except:
                    log.error("could not write to socket %s"%wsock)
                    self.observers.remove(wsock)
            else:
                self.observers.remove(wsock)
