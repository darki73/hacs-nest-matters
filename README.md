# Nest Matters

A Home Assistant integration that combines Google Nest and Matter thermostat entities into a unified climate control interface. This integration provides the best of both worlds: responsive temperature control via Matter (no rate limits) and full HVAC/fan features via Google Nest.

## Features

- **Unified Climate Entity**: Single interface combining Matter and Google Nest thermostats
- **Intelligent Routing**: Temperature changes via Matter (fast, no rate limits), HVAC/fan control via Google Nest (full features)
- **Auto-Discovery**: Automatically finds and pairs Matter + Google Nest thermostat combinations
- **Web UI Configuration**: Easy setup through Home Assistant UI, no YAML required
- **Real-time Updates**: Responsive temperature readings from Matter integration
- **Full Feature Support**: Access to all HVAC modes, fan controls, and humidity readings

## Prerequisites

### 1. Home Assistant
- **Home Assistant 2026.2.1** or newer is required.

### 2. Google Nest Integration
The [Google Nest integration](https://www.home-assistant.io/integrations/nest/) must be configured and your thermostat added to Home Assistant.

### 3. Matter Integration
The [Matter integration](https://www.home-assistant.io/integrations/matter/) must be enabled in Home Assistant.

### 4. Supported Hardware
- **Google Nest Learning Thermostat (4th Generation)** - This is the only supported model as it's the only Nest thermostat with Matter support.

## Setup Instructions

### Step 1: Enable Matter on Your Thermostat

1. On your Nest thermostat, navigate to:
   - **Settings** → **Matter** → **Link Another App** → **Enter Manually**
2. This will display a Matter pairing code
3. Use this code to add the thermostat to Home Assistant via the Matter integration

### Step 2: Configure Entity Names (Important!)

For auto-discovery to work properly, you need to rename your Matter thermostat entity:

1. Go to **Settings** → **Devices & Services** → **Entities**
2. Find your Matter thermostat entity
3. Click on the entity and select **"Generate new entity ID"**
4. Rename the thermostat so the Matter entity name follows this pattern:
   - **Google Nest entity**: `climate.living_room`
   - **Matter entity**: `climate.living_room_matter`

> **Note**: The Matter entity name must be the same as the Google Nest entity name plus `_matter` suffix for auto-discovery to work.

### Step 3: Install Nest Matters

#### Via HACS (Recommended)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=Integration&repository=hacs-nest-matters&owner=darki73)

#### Manual Installation
1. Download the latest release from [GitHub](https://github.com/darki73/hacs-nest-matters)
2. Extract the `nest_matters` folder to your `custom_components` directory
3. Restart Home Assistant

### Step 4: Configure the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Nest Matters"**
4. Follow the setup wizard:
   - If auto-discovery finds your thermostat pairs, select the one you want to configure
   - If auto-discovery doesn't work, choose manual configuration and select your Matter and Google Nest entities

## How It Works

The integration creates a unified climate entity that intelligently routes commands to the appropriate underlying entity. The entity is **push-based** — it subscribes to state change events from both source entities and updates instantly, with no polling.

Each unified thermostat appears as a proper device in the Home Assistant device registry.

### Temperature Control → Matter Entity
- **Why**: Matter operates locally with no rate limits and provides faster response
- **Used for**: Setting target temperature, reading current temperature

### HVAC & Fan Control → Google Nest Entity
- **Why**: Google Nest integration provides full feature access
- **Used for**: Changing HVAC modes (heat, cool, auto), fan settings, turn on/off, accessing humidity data

### State Display
- **Current Temperature**: From Matter entity (local, more responsive)
- **Target Temperature**: From Matter entity
- **HVAC Mode**: From Google Nest entity
- **Fan Mode**: From Google Nest entity
- **Humidity**: From Google Nest entity

## Configuration Options

### Auto-Discovery
If your entities are named correctly (e.g., `climate.living_room` and `climate.living_room_matter`), the integration will automatically discover available pairs during setup.

### Manual Configuration
If auto-discovery doesn't work, you can manually select:
- **Integration Name**: Display name for the unified entity
- **Matter Entity**: Your Matter thermostat entity
- **Google Nest Entity**: Your Google Nest thermostat entity

## Troubleshooting

### Auto-Discovery Not Working
1. Check that your Matter entity name ends with `_matter`
2. Ensure both entities are available and not in an error state
3. Verify entity names match the pattern: `climate.room_name` and `climate.room_name_matter`

### Entity Unavailable
1. Check that both the Google Nest and Matter integrations are working properly
2. Verify your thermostat is online and accessible
3. Check Home Assistant logs for any error messages

### Temperature Changes Not Working
1. Verify the Matter entity is responding to temperature changes
2. Check that the Matter integration is properly connected
3. Ensure the thermostat is not in an error state

## Advanced Usage

### Multiple Thermostats
You can set up multiple Nest Matters entities if you have multiple thermostats. Each thermostat pair will create its own unified entity.

### Automation Integration
The unified entity works with all Home Assistant automation features:

```yaml
automation:
  - alias: "Morning Temperature"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      service: climate.set_temperature
      target:
        entity_id: climate.living_room_unified
      data:
        temperature: 22
```

## Support

- **Issues**: [GitHub Issues](https://github.com/darki73/hacs-nest-matters/issues)
- **Documentation**: [GitHub Repository](https://github.com/darki73/hacs-nest-matters)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and updates.