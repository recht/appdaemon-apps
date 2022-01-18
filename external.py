import hassapi as hass
import time


class ExternalTemp(hass.Hass):
    def initialize(self):
        self.ieee = self.args['ieee']
        self.sensor = self.args['sensor']
        self.prev = -1
        self.last = time.time()

        self.listen_state(self.on_temp, self.sensor, immediate=True)

    def on_temp(self, entity, attribute, old, new, kwargs):
        if new == 'unavailable':
            return

        new = float(new)
        if abs(new - self.prev) >= 0.1 and self.last + 600 > time.time():
            self.log('updating external temp to %s', new)
            self.call_service('zha/set_zigbee_cluster_attribute', ieee=self.ieee, endpoint_id=1, cluster_id=0x201,
                              cluster_type='in', attribute=0x4015, value=int(new * 100))
            self.prev = new
            self.last = time.time()
