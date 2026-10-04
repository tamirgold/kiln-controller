import os
import secrets
from urllib.parse import urlsplit
import bottle
import gevent
from lib.settings_store import Store,SettingsError,GROUPS

def install(app,config,oven):
    store=Store(config)
    token=secrets.token_urlsafe(32)
    control={'restarting':False}
    def document():
        return dict(schema=store.schema(),groups=[dict(key=k,label=v) for k,v in GROUPS],
                    current=store.current,values=store.desired(),revision=store.revision(),pending=store.pending.exists(),
                    state=oven.state,can_apply=oven.state=='IDLE' and not oven.should_i_automatic_restart() and not control['restarting'],token=token)
    def guard():
        if bottle.request.headers.get('X-Kiln-Settings')!=token:bottle.abort(403,'Reload the settings page before making changes.')
        origin=bottle.request.headers.get('Origin')
        if origin and urlsplit(origin).netloc!=bottle.request.get_header('Host'):bottle.abort(403,'Origin does not match this controller.')
        if bottle.request.content_length>65536:bottle.abort(413,'Settings request is too large.')
        if control['restarting']:bottle.abort(409,'Controller is restarting.')
    def error(exc):
        bottle.response.status=409 if exc.errors.get('_conflict') else 400
        return dict(error=str(exc),fields=exc.errors)
    @app.get('/api/settings')
    def read():
        bottle.response.set_header('Cache-Control','no-store')
        return document()
    @app.post('/api/settings')
    def save():
        guard()
        try:
            body=bottle.request.json or {};store.save(body.get('values'),body.get('revision'))
            return document()
        except SettingsError as exc:return error(exc)
    @app.post('/api/settings/discard')
    def discard():
        guard()
        try:
            store.discard((bottle.request.json or {}).get('revision'));return document()
        except SettingsError as exc:return error(exc)
    @app.post('/api/settings/apply')
    def apply():
        guard()
        with oven._restart_lock:
            if oven.state!='IDLE' or oven.should_i_automatic_restart():
                bottle.response.status=409
                return dict(error='The kiln must be idle. Saved changes do not affect the current firing.')
            # Block all start paths before writing the active configuration.
            control['restarting']=True
            try:
                if hasattr(oven,'output'):oven.output.cool(0)
                oven.save_state()
                values=store.apply((bottle.request.json or {}).get('revision'))
            except SettingsError as exc:
                control['restarting']=False;return error(exc)
            except Exception:
                control['restarting']=False;raise
        # systemd restarts on a nonzero exit. No sudo or shell commands are exposed.
        gevent.spawn_later(1.5,lambda:os._exit(75))
        return dict(success=True,restarting=True,port=values['listening_port'])
    return control
