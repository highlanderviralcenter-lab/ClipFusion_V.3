import os
import yaml

class PlatformEngine:
    def __init__(self, config_path=None):
        if config_path is None:
            base_dir = os.path.dirname(__file__)
            config_path = os.path.join(base_dir, '..', 'config', 'platforms.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.platforms = yaml.safe_load(f)

    def get_platform(self, name):
        return self.platforms.get(name)

    def ideal_duration(self, platform_name):
        plat = self.get_platform(platform_name)
        if plat:
            return plat.get('ideal_duration', [30, 60])
        return [30, 60]

    def max_duration(self, platform_name):
        plat = self.get_platform(platform_name)
        return plat.get('max_duration', 180) if plat else 180
