### Installation
- create a new dir named `visionq` under `/config/custom_components` on your home assistant server
- copy `manifest.json`, `sensor.py` and `__init__.py` to `/config/custom_components/visionq`
- restart your home assistant
- include following in `/config/configuration.yaml`:
```yaml
sensor:
  - platform: visionq
    login: email_login # e.g. abc@gmail.com
    password_hash: visionq_password_hash # ask me how to get it
    poll_interval_seconds: 60
```
