import hassapi as hass
import threading
import time


class Haptek(hass.Hass):
    def initialize(self):
        self.dev_prefix = self.args['device']
        self.log('init')

        for b in [1, 2, 3, 4]:
            entity = self.args.get('button%s' % b)
            if not entity:
                continue
            if entity.startswith('light.'):
                LightButton(self, self.dev_prefix, b, entity, self.args.get('has_led'))
            elif entity.startswith('switch.'):
                SwitchButton(self, self.dev_prefix, b, entity)
            elif entity.startswith('input_select.'):
                SelectButton(self, self.dev_prefix, b, entity)


def handle_longpress(obj, hass, entity, handler):
    def wait():
        if not obj.light:
            return
        obj.longpress = False
        hass.log('sleeping')
        time.sleep(0.3)
        hass.log('done sleeping')
        state = hass.get_state(entity)
        hass.log('state after sleep: %s', state)
        obj.longpress = state == 'on'
        if state == 'on':
            handler()

    threading.Thread(target=wait).start()


class LightButton:

    def __init__(self, hass, prefix, num, light, has_led):
        if not light:
            return
        self.dev_prefix = prefix
        self.num = num
        self.hass = hass
        self.button_entity = self.button(num)
        self.light = light
        self.auto_brightness = -1
        self.has_led = has_led
        self.luminance = 0
        self.last_dir_up = False
        self.state = 'unknown'
        hass.listen_state(self.click, self.button_entity)
#        hass.listen_state(self.on_luminance, 'sensor.xiaomi_lumi_sen_ill_mgl01_a12f0a00_illuminance', immediate=True)
        hass.listen_state(self.on_state, light, immediate=True)

    def on_luminance(self, entity, attribute, old, new, kwargs):
        if new == 'unavailable':
            return
        self.hass.log('luminance: %s', new)
        self.luminance = float(new)
        if self.hass.get_state(self.light) == 'off':
            return
        if self.auto_brightness == self.hass.get_state(self.light, attribute='brightness'):
            self.hass.log('Adjust %s to %s', self.light, self.get_brightness())
            self.hass.turn_on(self.light, brightness=self.get_brightness())

    def click(self, entity, attribute, old, new, kwargs):
        self.hass.log('Clicked %s: %s %s %s %s', entity, attribute, old, new, kwargs)
        if attribute == 'state' and old == 'off' and new == 'on':
            handle_longpress(self, self.hass, self.button_entity, self.on_longpress)
        elif attribute == 'state' and old == 'on' and new == 'off':
            is_longpress = self.longpress
            if is_longpress:
                is_longpress = False
            else:
                self.on_click(entity)
            self.hass.log('Release on longpress: %s', is_longpress)

    def get_brightness(self):
        brightness = 255
        if self.luminance < 5:
            brightness = 100
        elif self.luminance < 10:
            brightness = 150
        elif self.luminance < 85:
            brightness = 200
        return brightness

    def on_click(self, entity):
        light = self.light
        if not light:
            self.hass.log('no light for %s', entity)
            return

        brightness = self.get_brightness()

        self.auto_brightness = brightness
        self.hass.log('click, state: %s', self.state)
        if self.state == 'on':
            self.hass.turn_off(light)
        else:
            # self.hass.turn_on(light, brightness=brightness)
            self.hass.fire_event('luminance_turn_on', light=light)

    def on_state(self, entity, attribute, old, new, kwargs):
        self.state = new
        if not self.has_led:
            return

        if new == 'on':
            self.hass.turn_on(self.led(), brightness=90, rgb_color=(255, 255, 255))
        else:
            self.hass.turn_off(self.led())

        self.hass.log('state: %s', new)

    def on_longpress(self):
        light = self.light
        if not light:
            return

        transition = 4
        end = 0

        target = 1 if self.last_dir_up else 254
        self.last_dir_up = not self.last_dir_up

        while self.hass.get_state(self.button_entity) == 'on':
            if time.time() > end or end == 0:
                brightness = self.hass.get_state(light, attribute='brightness') or 1
                target = 1 if self.last_dir_up else 254

                change = abs(brightness - target)
                ts = float(change) / float(254) * float(transition)
                end = time.time() + (change / 254) * transition + 1
                self.hass.log('turn on transition=%s brightness=%s change=%s current=%s', ts, target, change, brightness)
                self.hass.turn_on(light, transition=ts, brightness=target)

            time.sleep(0.1)

        self.hass.log('turn on done')
        self.hass.call_service('script/stop_light_transition', light=self.light)

    def button(self, n):
        return 'binary_sensor.%s_button_%d' % (self.dev_prefix, n)

    def led(self):
        if self.has_led:
            return 'light.%s_led%d' % (self.dev_prefix, self.num)
        else:
            return 'light.%s_led' % self.dev_prefix


class CoverButton:
    def __init__(self, hass, entity, cover):
        self.hass = hass
        self.entity = entity
        self.cover = cover
        hass.listen_state(self.on_state, cover, immediate=True, attribute='all')
        hass.listen_state(self.on_click, entity)

    def on_state(self, entity, attribute, old, new, kwargs):
        self.hass.log('cover state: %s %s %s %s %s', entity, attribute, old, new, kwargs)
        self.state = new['state']
        self.position = new['attributes'].get('current_position', 0)
        self.in_progress = False

    def on_click(self, entity, attribute, old, new, kwargs):
        if new == 'on':
            return
        if self.state == 'open':
            self.hass.call_service('cover/close', area_id='kontor')
            self.state = 'closed'
        else:
            self.hass.call_service('cover/open', area_id='kontor')
            self.state = 'open'
        self.in_progress = True


class SwitchButton:
    def __init__(self, hass, dev_prefix, num, switch):
        self.hass = hass
        self.switch = switch
        self.state = None
        self.button = 'binary_sensor.%s_button_%d' % (dev_prefix, num)
        hass.listen_state(self.on_click, self.button)
        #hass.listen_state(self.on_state, self.switch, immediate=True)

    def on_click(self, entity, attribute, old, new, kwargs):
        self.hass.log('switch click')
        if self.state == 'off':
            self.hass.turn_on(self.switch)
        else:
            self.hass.turn_off(self.switch)

    def on_state(self, entity, attribute, old, new, kwargs):
        self.state = new


class SelectButton:
    def __init__(self, hass, dev_prefix, num, input):
        self.hass = hass
        self.state = None
        self.input = input
        self.button = 'binary_sensor.%s_button_%d' % (dev_prefix, num)
        self.light = 'light.%s_led%d' % (dev_prefix, num)
        hass.listen_state(self.on_click, self.button)
        hass.listen_state(self.on_state, self.input, immediate=True)

    def on_state(self, entity, attribute, old, new, kwargs):
        self.state = new
        self.hass.log('new state: %s', new)
        if new == 'night':
            self.hass.turn_on(self.light, brightness=40, rgb_color=(0, 0, 255))
        else:
            self.hass.turn_off(self.light)

    def on_click(self, entity, attribute, old, new, kwargs):
        if attribute == 'state' and old == 'on' and new == 'off':
            if self.state == 'day':
                self.hass.set_state(self.input, state='night')
            else:
                self.hass.set_state(self.input, state='day')
