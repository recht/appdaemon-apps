import hassapi as hass


class Transition(hass.Hass):
    def initialize(self):
        self.listen_event(self.on_stop, 'transition_stop')
        self.log('init')
        for s in self.list_services():
            self.log('service %s', s)

    def on_stop(self, event, data, kwargs):
        self.log('event %s %s %s', event, data, kwargs)

        light = data['light']
        identifiers = data['identifiers'] or []

        zha = [i[1] for i in identifiers if i[0] == 'zha']
        if zha:
            self.call_service('zha/issue_zigbee_cluster_command', ieee=zha[0], endpoint_id=11, cluster_id=8,
                              cluster_type='in', command=3, command_type='server')
        else:
            self.turn_on(light, brightness_step=0, transition=0)

        state = self.get_state(data['light'], attribute='identifiers')
        self.log('on stop state: %s', state)
