#pragma once

#include "esphome/core/component.h"
#include "esphome/core/automation.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/uart/uart.h"

#include <cstddef>
#include <limits>
#include <vector>
#include "fpc_api.h"

namespace esphome {
namespace fingerprint_FPC2532 {
// using fpc::fpc_result_t; /* to avoid errors due to namespaces */
class FingerprintFPC2532Component : public PollingComponent, public uart::UARTDevice {
 public:
  void update() override;
  void setup() override;
  void dump_config() override;

  void set_sensing_pin(GPIOPin *sensing_pin) { this->sensing_pin_ = sensing_pin; }
  void set_sensor_power_pin(GPIOPin *sensor_power_pin) { this->sensor_power_pin_ = sensor_power_pin; }

 protected:
  bool get_parameters_();
  fpc::fpc_result_t fpc_hal_init(void);
  fpc::fpc_result_t fpc_hal_tx(uint8_t *data, std::size_t len);
  fpc::fpc_result_t fpc_hal_rx(uint8_t *data, std::size_t len);
  int fpc_hal_data_available(void);
  void fpc_hal_delay_ms(uint32_t ms);

  void sensor_wakeup_();
  void sensor_sleep_();

  GPIOPin *sensing_pin_{nullptr};
  GPIOPin *sensor_power_pin_{nullptr};
  uint32_t last_transfer_ms_ = 0;
};

}  // namespace fingerprint_FPC2532
}  // namespace esphome
