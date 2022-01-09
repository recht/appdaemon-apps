import hassapi as hass

class HumidityTrigger(hass.Hass):

    def initialize(self):
        self.entities = self.args['entities']
        self.monitor_entity = self.args['monitor']

        self.sensor_states = {e['sensor']: e for e in self.entities}
        self.outside = -1
        for e in self.entities:
            self.listen_state(self.on_switch_state, e['switch'], immediate=True, sensor=e['sensor'])
            self.listen_state(self.on_entity_state, e['sensor'], immediate=True)

        self.listen_state(self.on_humidity, self.monitor_entity, immediate=True)

    def on_humidity(self, entity, attribute, old, new, kwargs):
        self.log('humidity: %s %s %s %s %s', entity, attribute, old, new, kwargs)
        if new == 'unknown':
            return
        self.outside = float(new)
        self.adjust()

    def on_entity_state(self, entity, attribute, old, new, kwargs):
        self.log('state %s: %s->%s', entity, old, new)
        self.sensor_states[entity]['state'] = float(new)
        self.adjust_single(entity)

    def on_switch_state(self, entity, attribute, old, new, kwargs):
        self.sensor_states[kwargs['sensor']]['switch_state'] = new

    def adjust(self):
        if self.outside == -1:
            return
        for sensor in self.sensor_states:
            self.adjust_single(sensor)

    def adjust_single(self, sensor):
        if self.outside == -1:
            return
        sensor_state = self.sensor_states[sensor]['state']
        switch = self.sensor_states[sensor]['switch']
        switch_state = self.sensor_states[sensor]['switch_state']
        if sensor_state > self.outside:
            if switch_state == 'on':
                return
            self.log('Outside humidity %s is smaller than %s for %s, turning on', self.outside, sensor_state, switch)
            self.turn_on(switch)
        else:
            if switch_state == 'off':
                return
            self.log('Outside humidity %s is larger than %s for %s, turning off', self.outside, sensor_state, switch)
            self.turn_off(switch)
