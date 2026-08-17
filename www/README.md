# Custom Lovelace Cards

This directory contains custom Lovelace cards that are vendored into the repository and synced to the Home Assistant pod.

## template-entity-row

**Source:** https://github.com/thomasloven/lovelace-template-entity-row  
**Version:** v1.4.1  
**File:** `template-entity-row.js`

The `template-entity-row` custom card is a Lovelace entity row that allows rendering templated content for entity display, including secondary information not available in the stock Entities card.

### Installation

The card is served at `/local/template-entity-row.js` and is already vendored in this repository.

To use it on a live Home Assistant instance, you must manually register it as a resource:

1. Go to **Settings** → **Dashboards**
2. Click the three-dot menu (⋮) in the top right
3. Select **Resources**
4. Click **Create Resource**
5. Set **URL** to `/local/template-entity-row.js`
6. Set **Resource type** to **JavaScript Module**
7. Click **Create**
8. Hard-refresh your browser (Cmd+Shift+R or Ctrl+Shift+R)

### Example Usage

Add a row to your dashboard YAML or via the UI:

```yaml
- type: custom:template-entity-row
  entity: switch.office_heater
  secondary: "{{ states('sensor.<REAL_POWER_ENTITY>') }} W"
```

**Note:** Replace `<REAL_POWER_ENTITY>` with the actual power sensor entity ID for the device (e.g. `sensor.office_heater_power`). Find your entity IDs in **Developer Tools** → **States**.

In the UI, the row will display the entity's primary state (e.g. "on" / "off") and the secondary line with the rendered template (e.g. "42.5 W").

### Why vendored?

This repository is git-managed and synced to a Kubernetes pod running Home Assistant. The card is vendored here rather than installed via HACS so it syncs automatically with the configuration.
