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
            self.listen_state(self.on_humidity_state, e['humidity'], immediate=True, sensor=e['sensor'])

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

    def on_humidity_state(self, entity, attribute, old, new, kwargs):
        self.sensor_states[kwargs['sensor']]['humidity'] = float(new) if new != 'unavailable' else 100.0

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
        humidity = self.sensor_states[sensor]['humidity']
        if sensor_state > self.outside and humidity >= 45:
            if switch_state == 'on':
                return
            self.log('%s: Outside humidity %s is smaller than %s for %s, relative %s, turning on',
                     sensor, self.outside, sensor_state, switch, humidity)
            self.turn_on(switch)
        elif sensor_state <= self.outside or humidity <= 41:
            if switch_state == 'off':
                return
            self.log('%s: Outside humidity %s is larger than %s for %s, relative %s, turning off',
                     sensor, self.outside, sensor_state, switch, humidity)
            self.turn_off(switch)

