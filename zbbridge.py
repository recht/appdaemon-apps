import hassapi as hass
import requests


class ZBBridge(hass.Hass):
    def initialize(self):
        self.ip = self.args['ip']
        self.listen_event(self.reboot, 'zbbridge_reboot')

    def reboot(self, event, data, kwargs):
        self.log('reboot %s', self.ip)
        self.log('reboot: %s', requests.get('http://{}/cm?cmnd=Restart%201'.format(self.ip)))
