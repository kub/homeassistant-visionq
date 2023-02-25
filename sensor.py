import logging
import time
from datetime import timedelta, datetime

import requests
from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

SIGNAL = 'visionq'
DOMAIN = 'visionq'

_LOGGER = logging.getLogger('visionq')


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None) -> True:
    _LOGGER.info(str(config))
    sensor_connector = SensorConnector(hass, config['login'], config['password_hash'])
    # Do first update
    await hass.async_add_executor_job(sensor_connector.update)

    # Poll for updates in the background
    async_track_time_interval(
        hass,
        lambda now: sensor_connector.update(),
        timedelta(seconds=int(config['poll_interval_seconds'])),
    )

    entities: list[SensorEntity] = []
    entities.extend([VisionqSensor(sensor_connector, 'low_rate_consumption'),
                     VisionqSensor(sensor_connector, 'high_rate_consumption')])
    async_add_entities(entities, True)

    hass.data.setdefault(DOMAIN, {})


class VisionqSensor(SensorEntity):
    def __init__(self, sensor_connector, variable):
        super().__init__()
        self.sensor_connector = sensor_connector
        self.variable = variable

        self._state = None
        self._state_attributes = None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL, self._async_update_callback)
        )

    @callback
    def _async_update_callback(self):
        self._async_update_data()
        self.async_write_ha_state()

    @property
    def unique_id(self):
        return f"{'visionq'} {self.variable}"

    @property
    def name(self):
        return f"{'visionq'} {self.variable}"

    @property
    def native_value(self):
        return self._state

    @property
    def state_class(self):
        return SensorStateClass.TOTAL_INCREASING

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def native_unit_of_measurement(self):
        return UnitOfEnergy.KILO_WATT_HOUR

    @callback
    def _async_update_data(self):
        self._state = self.sensor_connector.data[self.variable]


class SensorConnector:
    def __init__(self, hass, login, password_hash):
        self.hass = hass
        self.login = login
        self.password_hash = password_hash
        self.data = {
            'low_rate_consumption': None,
            'high_rate_consumption': None,
        }

    def convert_to_int(self, value) -> int:
        return int(value.split('.')[0])

    def update(self):
        try:
            token = requests.get(f"https://app.visionq.cz/index.php",
                                 cookies={'email': self.login, 'password': self.password_hash}).cookies['PHPSESSID']

            time_from = time.mktime((datetime.now() - timedelta(hours=1)).timetuple()) * 1000
            payload = requests.get(
                f"https://app.visionq.cz/data/pages/export/csv.php?from={time_from}&to=&predefined=today&id=3128",
                cookies={'PHPSESSID': token}).text

            last_value = payload.splitlines()[1]
            high = last_value.split(', ')[2]
            low = last_value.split(', ')[3]
            self.data['low_rate_consumption'] = self.convert_to_int(low)
            self.data['high_rate_consumption'] = self.convert_to_int(high)

            dispatcher_send(self.hass, SIGNAL)
        except:
            _LOGGER.error("can't connect to Visionq")
