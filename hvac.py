import datetime
import hassapi as hass


class HVAC(hass.Hass):
    def initialize(self):
        self.expected = {}
        self.temps = {}
        self.managed = {}
        self.modes = self.args['modes']
        for s in self.args['schedules']:
            for e in s['entities']:
                self.listen_state(self.on_state, e, attribute='all', immediate=True)
                self.listen_state(self.on_load_estimate, e, attribute='load_estimate', count=len(s['entities']), ieee=self.args['addresses'][e])
                self.run_every(self.read_load, 'now', 300, entity=e)
            self.run_minutely(self.ensure, datetime.time(0, 0, 0), schedule=s)

    def on_state(self, entity, attribute, old, new, kwargs):
        self.log('state: %s %s', entity, new)
        if new['state'] == 'unavailable':
            return
        temp = float(new['attributes']['temperature'])
        self.temps[entity] = temp

    def on_load_estimate(self, entity, attribute, old, new, kwargs):
        if new is None or new == 'unavailable':
            return
        if kwargs['count'] == 1:
            return

        val = int(new / kwargs['count'])
        self.log('Adjust load estimate on %s to %s', entity, val)
        self.call_service('zha/set_zigbee_cluster_attribute', ieee=kwargs['ieee'], endpoint_id=1, cluster_id=0x201,
                          cluster_type='in', attribute=0x404a, value=val)

    def ensure(self, kwargs):
        schedule = kwargs['schedule']
        self.log('adjust: %s', schedule)

        now = datetime.datetime.now().time()
        for s in reversed(schedule['schedule']):
            self.log('schedule: %s', s)
            dt, mode = next(iter(s.items()))
            t = self.parse_time(dt)
            if now >= t:
                target = self.modes[mode]['temp']
                self.log('%s should be %s', schedule['entities'], mode)
                for e in schedule['entities']:
                    self.expected[e] = target
                    if e not in self.temps:
                        continue

                    if self.temps[e] != target and self.managed.get(e) == mode:
                        self.log('manual adjustment of %s, skipping until next mode', e)
                        continue

                    if not self.temps.get(e) == target:
                        self.log('setting temp on %s to %s', e, target)
                        self.call_service('climate/set_temperature', entity_id=e, temperature=target)
                    self.managed[e] = mode
                break

    def read_load(self, kwargs):
        entity = kwargs['entity']
        self.call_service('zha_custom/execute', command='attr_read', ieee=entity, endpoint=1, cluster=0x201, attribute=0x404a, state_id=entity, state_attr='load_estimate')
        # self.call_service('zha_custom/execute', command='attr_read', ieee=entity, endpoint=1, cluster=0x201, attribute=0x4040, state_id=entity, state_attr='load_room_mean')
