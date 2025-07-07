# ESPHome Integration Tests

This directory contains end-to-end integration tests for ESPHome, focusing on testing the complete flow from YAML configuration to running devices with API connections.

## Structure

- `conftest.py` - Common fixtures and utilities
- `const.py` - Constants used throughout the integration tests
- `types.py` - Type definitions for fixtures and functions
- `fixtures/` - YAML configuration files for tests
- `test_*.py` - Individual test files

## How it works

### Automatic YAML Loading

The `yaml_config` fixture automatically loads YAML configurations based on the test name:
- It looks for a file named after the test function (e.g., `test_host_mode_basic` → `fixtures/host_mode_basic.yaml`)
- The fixture file must exist or the test will fail with a clear error message
- The fixture automatically injects a dynamic port number into the API configuration

### Key Fixtures

- `run_compiled` - Combines write, compile, and run operations into a single context manager
- `api_client_connected` - Creates an API client that automatically connects using ReconnectLogic
- `reserved_tcp_port` - Reserves a TCP port by holding the socket open until ESPHome needs it
- `unused_tcp_port` - Provides the reserved port number for each test

### Writing Tests

The simplest way to write a test is to use the `run_compiled` and `api_client_connected` fixtures:

```python
@pytest.mark.asyncio
async def test_my_feature(
    yaml_config: str,
    run_compiled: RunCompiledFunction,
    api_client_connected: APIClientConnectedFactory,
) -> None:
    # Write, compile and run the ESPHome device, then connect to API
    async with run_compiled(yaml_config), api_client_connected() as client:
        # Test your feature using the connected client
        device_info = await client.device_info()
        assert device_info is not None
```

### Creating YAML Fixtures

Create a YAML file in the `fixtures/` directory with the same name as your test function (without the `test_` prefix):

```yaml
# fixtures/my_feature.yaml
esphome:
  name: my-test-device
host:
api:  # Port will be automatically injected
logger:
# Add your components here
```

## Running Tests

```bash
# Run all integration tests
script/integration_test

# Run a specific test
pytest -vv tests/integration/test_host_mode_basic.py

# Debug compilation errors or see ESPHome output
pytest -s tests/integration/test_host_mode_basic.py
```

## Implementation Details

- Tests automatically wait for the API port to be available before connecting
- Process cleanup is handled automatically, with graceful shutdown using SIGINT
- Each test gets its own temporary directory and unique port
- Port allocation minimizes race conditions by holding the socket until just before ESPHome starts
- Output from ESPHome processes is displayed for debugging

## Integration Test Writing Guide

### Test Patterns and Best Practices

#### 1. Test File Naming Convention
- Use descriptive names: `test_{category}_{feature}.py`
- Common categories: `host_mode`, `api`, `scheduler`, `light`, `areas_and_devices`
- Examples:
  - `test_host_mode_basic.py` - Basic host mode functionality
  - `test_api_message_batching.py` - API message batching
  - `test_scheduler_stress.py` - Scheduler stress testing

#### 2. Essential Imports
```python
from __future__ import annotations

import asyncio
from typing import Any

import pytest
from aioesphomeapi import EntityState, SensorState

from .types import APIClientConnectedFactory, RunCompiledFunction
```

#### 3. Common Test Patterns

##### Basic Entity Test
```python
@pytest.mark.asyncio
async def test_my_sensor(
    yaml_config: str,
    run_compiled: RunCompiledFunction,
    api_client_connected: APIClientConnectedFactory,
) -> None:
    """Test sensor functionality."""
    async with run_compiled(yaml_config), api_client_connected() as client:
        # Get entity list
        entities, services = await client.list_entities_services()

        # Find specific entity
        sensor = next((e for e in entities if e.object_id == "my_sensor"), None)
        assert sensor is not None
```

##### State Subscription Pattern
```python
# Track state changes with futures
loop = asyncio.get_running_loop()
states: dict[int, EntityState] = {}
state_future: asyncio.Future[EntityState] = loop.create_future()

def on_state(state: EntityState) -> None:
    states[state.key] = state
    # Check for specific condition using isinstance
    if isinstance(state, SensorState) and state.state == expected_value:
        if not state_future.done():
            state_future.set_result(state)

client.subscribe_states(on_state)

# Wait for state with timeout
try:
    result = await asyncio.wait_for(state_future, timeout=5.0)
except asyncio.TimeoutError:
    pytest.fail(f"Expected state not received. Got: {list(states.values())}")
```

##### Service Execution Pattern
```python
# Find and execute service
entities, services = await client.list_entities_services()
my_service = next((s for s in services if s.name == "my_service"), None)
assert my_service is not None

# Execute with parameters
client.execute_service(my_service, {"param1": "value1", "param2": 42})
```

##### Multiple Entity Tracking
```python
# For tests with many entities
loop = asyncio.get_running_loop()
entity_count = 50
received_states: set[int] = set()
all_states_future: asyncio.Future[bool] = loop.create_future()

def on_state(state: EntityState) -> None:
    received_states.add(state.key)
    if len(received_states) >= entity_count and not all_states_future.done():
        all_states_future.set_result(True)

client.subscribe_states(on_state)
await asyncio.wait_for(all_states_future, timeout=10.0)
```

#### 4. YAML Fixture Guidelines

##### Naming Convention
- Match test function name: `test_my_feature` → `fixtures/my_feature.yaml`
- Note: Remove `test_` prefix for fixture filename

##### Basic Structure
```yaml
esphome:
  name: test-name  # Use kebab-case
  # Optional: areas, devices, platformio_options

host:  # Always use host platform for integration tests
api:   # Port injected automatically
logger:
  level: DEBUG  # Optional: Set log level

# Component configurations
sensor:
  - platform: template
    name: "My Sensor"
    id: my_sensor
    lambda: return 42.0;
    update_interval: 0.1s  # Fast updates for testing
```

##### Advanced Features
```yaml
# External components for custom test code
external_components:
  - source:
      type: local
      path: EXTERNAL_COMPONENT_PATH  # Replaced by test framework
    components: [my_test_component]

# Areas and devices
esphome:
  name: test-device
  areas:
    - id: living_room
      name: "Living Room"
    - id: kitchen
      name: "Kitchen"
      parent_id: living_room
  devices:
    - id: my_device
      name: "Test Device"
      area_id: living_room

# API services
api:
  services:
    - service: test_service
      variables:
        my_param: string
      then:
        - logger.log:
            format: "Service called with: %s"
            args: [my_param.c_str()]
```

#### 5. Testing Complex Scenarios

##### External Components
Create C++ components in `fixtures/external_components/` for:
- Stress testing
- Custom entity behaviors
- Scheduler testing
- Memory management tests

##### Log Line Monitoring
```python
log_lines: list[str] = []

def on_log_line(line: str) -> None:
    log_lines.append(line)
    if "expected message" in line:
        # Handle specific log messages

async with run_compiled(yaml_config, line_callback=on_log_line):
    # Test implementation
```

Example using futures for specific log patterns:
```python
import re

loop = asyncio.get_running_loop()
connected_future = loop.create_future()
service_future = loop.create_future()

# Patterns to match
connected_pattern = re.compile(r"Client .* connected from")
service_pattern = re.compile(r"Service called")

def check_output(line: str) -> None:
    """Check log output for expected messages."""
    if not connected_future.done() and connected_pattern.search(line):
        connected_future.set_result(True)
    elif not service_future.done() and service_pattern.search(line):
        service_future.set_result(True)

async with run_compiled(yaml_config, line_callback=check_output):
    async with api_client_connected() as client:
        # Wait for specific log message
        await asyncio.wait_for(connected_future, timeout=5.0)

        # Do test actions...

        # Wait for service log
        await asyncio.wait_for(service_future, timeout=5.0)
```

**Note**: Tests that monitor log messages typically have fewer race conditions compared to state-based testing, making them more reliable. However, be aware that the host platform currently does not have a thread-safe logger, so logging from threads will not work correctly.

##### Timeout Handling
```python
# Always use timeouts for async operations
try:
    result = await asyncio.wait_for(some_future, timeout=5.0)
except asyncio.TimeoutError:
    pytest.fail("Operation timed out - check test expectations")
```

#### 6. Common Assertions

```python
# Device info
assert device_info.name == "expected-name"
assert device_info.compilation_time is not None

# Entity properties
assert sensor.accuracy_decimals == 2
assert sensor.state_class == 1  # measurement
assert sensor.force_update is True

# Service availability
assert len(services) > 0
assert any(s.name == "expected_service" for s in services)

# State values
assert state.state == expected_value
assert state.missing_state is False
```

#### 7. Debugging Tips

- Use `pytest -s` to see ESPHome output during tests
- Add descriptive failure messages to assertions
- Use `pytest.fail()` with detailed error info for timeouts
- Check `log_lines` for compilation or runtime errors
- Enable debug logging in YAML fixtures when needed

#### 8. Performance Considerations

- Use short update intervals (0.1s) for faster tests
- Set reasonable timeouts (5-10s for most operations)
- Batch multiple assertions when possible
- Clean up resources properly using context managers

#### 9. Test Categories

- **Basic Tests**: Minimal functionality verification
- **Entity Tests**: Sensor, switch, light behavior
- **API Tests**: Message batching, services, events
- **Scheduler Tests**: Timing, defer operations, stress
- **Memory Tests**: Conditional compilation, optimization
- **Integration Tests**: Areas, devices, complex interactions
