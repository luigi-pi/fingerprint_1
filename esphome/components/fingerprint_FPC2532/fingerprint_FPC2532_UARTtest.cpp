#include "fingerprint_FPC2532.h"
#include "esphome/core/log.h"
#include <cinttypes>
#include "fpc_api.h"

namespace esphome {
namespace fingerprint_FPC2532 {

static const char *const TAG = "fingerprint_FPC2532";

void FingerprintFPC2532Component::update() {}

void FingerprintFPC2532Component::setup() {
  this->fpc_hal_init();
  // this->get_parameters_();  // added
}

/*
------------------------
HAL FUNCTIONS DEFINITONS
------------------------
*/
fpc_result_t FingerprintFPC2532Component::fpc_hal_init(void) { return FPC_RESULT_OK; }
fpc_result_t FingerprintFPC2532Component::fpc_hal_tx(uint8_t *data, std::size_t len) {
  if (!data || len == 0) {
    return FPC_RESULT_FAILURE;
  }
  // while (this->available()){
  //  result = this->fpc_host_sample_handle_rx_data();
  // if (result != FPC_RESULT_OK) {
  //  ESP_LOGCONFIG(TAG, " Failed to handle RX data, error %d", result);
  //  break;
  // }
  this->write_array(data, len);
  return FPC_RESULT_OK;  // doesn't guarantee array was actually sent: no timeout handling here
}
fpc_result_t FingerprintFPC2532Component::fpc_hal_rx(uint8_t *data, std::size_t len) {
  int rc = 0;
  rc = !this->read_array(data, len);

  return rc == 0 ? FPC_RESULT_OK : FPC_RESULT_FAILURE;
}
void FingerprintFPC2532Component::fpc_hal_delay_ms(uint32_t ms) { delay(ms); }
void FingerprintFPC2532Component::dump_config() {}

}  // namespace fingerprint_FPC2532
}  // namespace esphome
