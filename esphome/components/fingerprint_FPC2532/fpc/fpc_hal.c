/*
 * Copyright (c) 2024 Fingerprint Cards AB
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * @file    fpc_hal.c
 * @brief   Implementation of the fpc_hal API.
 */

// #include <stdarg.h>
// #include <unistd.h>
//#include <string.h>

// #include "dcache.h"
// #include "icache.h"
// #include "gpdma.h"
// #include "gpio.h"
// #include "spi_host.h"
// #include "uart_debug.h"
// #include "uart_host.h"
// #include "hal_common.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "fpc_api.h"
#include "fpc_hal.h"

static const char *TAG = "fpc_hal";
// extern void SystemClock_Config(void);

fpc_result_t fpc_hal_init(void) { return FPC_RESULT_OK; }

fpc_result_t fpc_hal_tx(uint8_t *data, size_t len, uint32_t timeout, int flush) {
  int rc = uart_host_transmit(data, len, timeout, flush);

  return rc == 0 ? FPC_RESULT_OK : FPC_RESULT_FAILURE;
}

fpc_result_t fpc_hal_rx(uint8_t *data, size_t len, uint32_t timeout) {
#if defined(HOST_IF_UART)
  int rc = uart_host_receive(data, len, timeout);
#elif defined(HOST_IF_SPI)
  int rc = spi_host_receive(data, len, timeout);
#endif
  return rc == 0 ? FPC_RESULT_OK : FPC_RESULT_FAILURE;
}

int fpc_hal_data_available(void) {
#if defined(HOST_IF_UART)
  return uart_host_rx_data_available();
#elif defined(HOST_IF_SPI)
  return spi_host_rx_data_available();
#endif
}

fpc_result_t fpc_hal_wfi(void) {
  __WFI();
  return FPC_RESULT_OK;
}

void fpc_hal_delay_ms(uint32_t ms) { HAL_Delay(ms); }

void fpc_sample_logf(const char *format, ...) {
#ifdef DEBUG
  va_list arglist;

  va_start(arglist, format);
  uart_debug_vprintf(format, arglist);
  va_end(arglist);
#endif
}
