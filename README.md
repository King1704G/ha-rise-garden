# Rise Gardens Integration for Home Assistant

A custom Home Assistant integration for [Rise Gardens](https://risegardens.com/) indoor hydroponic gardens.

## Features

- **Light Control**: Turn lights on/off and adjust brightness (0-100%)
- **Water Level Monitoring**: Track water level percentage and depth
- **Temperature Sensor**: Monitor ambient temperature
- **Online Status**: See if your garden is connected
- **Task Tracking**: View pending care tasks (feeding, harvesting, etc.)

## Supported Devices

- Rise Gardens Floor Unit (V2)
- Rise Gardens Personal Garden
- Rise Gardens Family Garden

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Add"
7. Search for "Rise Gardens" and install it
8. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/rise_garden` folder from this repository
2. Copy it to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Rise Gardens**
4. Enter your Rise Gardens app credentials (email and password)
5. Click **Submit**

## Entities

For each garden, the following entities are created:

| Entity | Type | Description |
|--------|------|-------------|
| `light.<garden_name>_light` | Light | Control garden lights with brightness |
| `sensor.<garden_name>_water_level` | Sensor | Water level as percentage |
| `sensor.<garden_name>_water_depth` | Sensor | Water depth in millimeters |
| `sensor.<garden_name>_temperature` | Sensor | Ambient temperature in °C |
| `sensor.<garden_name>_online` | Sensor | Garden connectivity status |
| `sensor.<garden_name>_pending_tasks` | Sensor | Number of pending care tasks |

## Example Automations

### Turn off lights at night
```yaml
automation:
  - alias: "Rise Garden Lights Off at Night"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: light.turn_off
        target:
          entity_id: light.herb_light
```

### Notify when water is low
```yaml
automation:
  - alias: "Rise Garden Low Water Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.herb_water_level
        below: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Your Rise Garden needs water!"
```

## API Reference

This integration uses the Rise Gardens cloud API:
- Authentication: Auth0 with password-realm grant
- Base URL: `https://prod-api.risegds.com/v2`

## Troubleshooting

### Integration not loading
- Ensure you're using the same email/password as the Rise Gardens mobile app
- Check Home Assistant logs for error messages

### Garden shows as offline
- Verify your garden is connected to WiFi
- Check the Rise Gardens app to confirm connectivity

### Sensors showing "Unknown"
- The garden may be offline
- Wait for the next update interval (60 seconds)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

This is an unofficial integration and is not affiliated with Rise Gardens. Use at your own risk.
