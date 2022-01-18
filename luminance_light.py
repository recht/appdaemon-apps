import hassapi as hass


class Light(hass.Hass):
    def initialize(self):
        self.managed = {}
        self.sensor = self.args.get('sensor')
        self.luminance = 0
        self.listen_event(self.on_turn_on, 'luminance_turn_on')
        self.listen_event(self.on_turn_off, 'luminance_turn_off')
        self.listen_state(self.on_luminance, self.sensor, immediate=True)

    def on_luminance(self, entity, attribute, old, new, kwargs):
        if new == 'unavailable':
            return
        self.log('luminance: %s', new)
        old = self.get_brightness()
        self.luminance = float(new)
        new = self.get_brightness()
        if new == old:
            return

        remove = []
        for light, brightness in self.managed.items():
            if self.get_state(light) == 'off':
                remove.append(light)
                continue

            if brightness == self.get_state(light, attribute='brightness'):
                self.log('Adjust %s to %s', light, new)
                self.turn_on(light, brightness=new)
                self.managed[light] = new
            else:
                remove.append(light)

        for light in remove:
            del self.managed[light]

    def get_brightness(self):
        brightness = 255
        if self.luminance < 5:
            brightness = 100
        elif self.luminance < 10:
            brightness = 150
        elif self.luminance < 85:
            brightness = 200
        return brightness

    def on_turn_on(self, event, data, kwargs):
        self.log('turn_on %s %s', event, data)
        brightness = self.get_brightness()
        lights = data['light']
        if not isinstance(lights, list):
            lights = [lights]

        for light in lights:
            self.turn_on(light, brightness=brightness, **data.get('kwargs', {}))
            self.managed[light] = brightness

    def on_turn_off(self, event, data, kwargs):
        self.log('turn_off %s %s', event, data)
