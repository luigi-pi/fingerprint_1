#include "api_server.h"
#ifdef USE_API
#include <cerrno>
#include "api_connection.h"
#include "esphome/components/network/util.h"
#include "esphome/core/application.h"
#include "esphome/core/defines.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"
#include "esphome/core/util.h"
#include "esphome/core/version.h"

#ifdef USE_LOGGER
#include "esphome/components/logger/logger.h"
#endif

#include <algorithm>

namespace esphome {
namespace api {

static const char *const TAG = "api";

// APIServer
APIServer *global_api_server = nullptr;  // NOLINT(cppcoreguidelines-avoid-non-const-global-variables)

#ifndef USE_API_YAML_SERVICES
// Global empty vector to avoid guard variables (saves 8 bytes)
// This is initialized at program startup before any threads
static const std::vector<UserServiceDescriptor *> empty_user_services{};

const std::vector<UserServiceDescriptor *> &get_empty_user_services_instance() { return empty_user_services; }
#endif

APIServer::APIServer() {
  global_api_server = this;
  // Pre-allocate shared write buffer
  shared_write_buffer_.reserve(64);
}

void APIServer::setup() {
  ESP_LOGCONFIG(TAG, "Running setup");
  this->setup_controller();

#ifdef USE_API_NOISE
  uint32_t hash = 88491486UL;

  this->noise_pref_ = global_preferences->make_preference<SavedNoisePsk>(hash, true);

  SavedNoisePsk noise_pref_saved{};
  if (this->noise_pref_.load(&noise_pref_saved)) {
    ESP_LOGD(TAG, "Loaded saved Noise PSK");

    this->set_noise_psk(noise_pref_saved.psk);
  }
#endif

  // Schedule reboot if no clients connect within timeout
  if (this->reboot_timeout_ != 0) {
    this->schedule_reboot_timeout_();
  }

  this->socket_ = socket::socket_ip_loop_monitored(SOCK_STREAM, 0);  // monitored for incoming connections
  if (this->socket_ == nullptr) {
    ESP_LOGW(TAG, "Could not create socket");
    this->mark_failed();
    return;
  }
  int enable = 1;
  int err = this->socket_->setsockopt(SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(int));
  if (err != 0) {
    ESP_LOGW(TAG, "Socket unable to set reuseaddr: errno %d", err);
    // we can still continue
  }
  err = this->socket_->setblocking(false);
  if (err != 0) {
    ESP_LOGW(TAG, "Socket unable to set nonblocking mode: errno %d", err);
    this->mark_failed();
    return;
  }

  struct sockaddr_storage server;

  socklen_t sl = socket::set_sockaddr_any((struct sockaddr *) &server, sizeof(server), this->port_);
  if (sl == 0) {
    ESP_LOGW(TAG, "Socket unable to set sockaddr: errno %d", errno);
    this->mark_failed();
    return;
  }

  err = this->socket_->bind((struct sockaddr *) &server, sl);
  if (err != 0) {
    ESP_LOGW(TAG, "Socket unable to bind: errno %d", errno);
    this->mark_failed();
    return;
  }

  err = this->socket_->listen(4);
  if (err != 0) {
    ESP_LOGW(TAG, "Socket unable to listen: errno %d", errno);
    this->mark_failed();
    return;
  }

#ifdef USE_LOGGER
  if (logger::global_logger != nullptr) {
    logger::global_logger->add_on_log_callback([this](int level, const char *tag, const char *message) {
      if (this->shutting_down_) {
        // Don't try to send logs during shutdown
        // as it could result in a recursion and
        // we would be filling a buffer we are trying to clear
        return;
      }
      for (auto &c : this->clients_) {
        if (!c->flags_.remove)
          c->try_send_log_message(level, tag, message);
      }
    });
  }
#endif

#ifdef USE_CAMERA
  if (camera::Camera::instance() != nullptr && !camera::Camera::instance()->is_internal()) {
    camera::Camera::instance()->add_image_callback([this](const std::shared_ptr<camera::CameraImage> &image) {
      for (auto &c : this->clients_) {
        if (!c->flags_.remove)
          c->set_camera_state(image);
      }
    });
  }
#endif
}

void APIServer::schedule_reboot_timeout_() {
  this->status_set_warning();
  this->set_timeout("api_reboot", this->reboot_timeout_, []() {
    if (!global_api_server->is_connected()) {
      ESP_LOGE(TAG, "No clients; rebooting");
      App.reboot();
    }
  });
}

void APIServer::loop() {
  // Accept new clients only if the socket exists and has incoming connections
  if (this->socket_ && this->socket_->ready()) {
    while (true) {
      struct sockaddr_storage source_addr;
      socklen_t addr_len = sizeof(source_addr);
      auto sock = this->socket_->accept_loop_monitored((struct sockaddr *) &source_addr, &addr_len);
      if (!sock)
        break;
      ESP_LOGD(TAG, "Accept %s", sock->getpeername().c_str());

      auto *conn = new APIConnection(std::move(sock), this);
      this->clients_.emplace_back(conn);
      conn->start();

      // Clear warning status and cancel reboot when first client connects
      if (this->clients_.size() == 1 && this->reboot_timeout_ != 0) {
        this->status_clear_warning();
        this->cancel_timeout("api_reboot");
      }
    }
  }

  if (this->clients_.empty()) {
    return;
  }

  // Process clients and remove disconnected ones in a single pass
  // Check network connectivity once for all clients
  if (!network::is_connected()) {
    // Network is down - disconnect all clients
    for (auto &client : this->clients_) {
      client->on_fatal_error();
      ESP_LOGW(TAG, "%s: Network down; disconnect", client->get_client_combined_info().c_str());
    }
    // Continue to process and clean up the clients below
  }

  size_t client_index = 0;
  while (client_index < this->clients_.size()) {
    auto &client = this->clients_[client_index];

    if (!client->flags_.remove) {
      // Common case: process active client
      client->loop();
      client_index++;
      continue;
    }

    // Rare case: handle disconnection
#ifdef USE_API_CLIENT_DISCONNECTED_TRIGGER
    this->client_disconnected_trigger_->trigger(client->client_info_, client->client_peername_);
#endif
    ESP_LOGV(TAG, "Remove connection %s", client->client_info_.c_str());

    // Swap with the last element and pop (avoids expensive vector shifts)
    if (client_index < this->clients_.size() - 1) {
      std::swap(this->clients_[client_index], this->clients_.back());
    }
    this->clients_.pop_back();

    // Schedule reboot when last client disconnects
    if (this->clients_.empty() && this->reboot_timeout_ != 0) {
      this->schedule_reboot_timeout_();
    }
    // Don't increment client_index since we need to process the swapped element
  }
}

void APIServer::dump_config() {
  ESP_LOGCONFIG(TAG,
                "API Server:\n"
                "  Address: %s:%u",
                network::get_use_address().c_str(), this->port_);
#ifdef USE_API_NOISE
  ESP_LOGCONFIG(TAG, "  Using noise encryption: %s", YESNO(this->noise_ctx_->has_psk()));
  if (!this->noise_ctx_->has_psk()) {
    ESP_LOGCONFIG(TAG, "  Supports noise encryption: YES");
  }
#else
  ESP_LOGCONFIG(TAG, "  Using noise encryption: NO");
#endif
}

#ifdef USE_API_PASSWORD
bool APIServer::uses_password() const { return !this->password_.empty(); }

bool APIServer::check_password(const std::string &password) const {
  // depend only on input password length
  const char *a = this->password_.c_str();
  uint32_t len_a = this->password_.length();
  const char *b = password.c_str();
  uint32_t len_b = password.length();

  // disable optimization with volatile
  volatile uint32_t length = len_b;
  volatile const char *left = nullptr;
  volatile const char *right = b;
  uint8_t result = 0;

  if (len_a == length) {
    left = *((volatile const char **) &a);
    result = 0;
  }
  if (len_a != length) {
    left = b;
    result = 1;
  }

  for (size_t i = 0; i < length; i++) {
    result |= *left++ ^ *right++;  // NOLINT
  }

  return result == 0;
}
#endif

void APIServer::handle_disconnect(APIConnection *conn) {}

#ifdef USE_BINARY_SENSOR
void APIServer::on_binary_sensor_update(binary_sensor::BinarySensor *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_binary_sensor_state(obj);
}
#endif

#ifdef USE_COVER
void APIServer::on_cover_update(cover::Cover *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_cover_state(obj);
}
#endif

#ifdef USE_FAN
void APIServer::on_fan_update(fan::Fan *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_fan_state(obj);
}
#endif

#ifdef USE_LIGHT
void APIServer::on_light_update(light::LightState *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_light_state(obj);
}
#endif

#ifdef USE_SENSOR
void APIServer::on_sensor_update(sensor::Sensor *obj, float state) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_sensor_state(obj);
}
#endif

#ifdef USE_SWITCH
void APIServer::on_switch_update(switch_::Switch *obj, bool state) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_switch_state(obj);
}
#endif

#ifdef USE_TEXT_SENSOR
void APIServer::on_text_sensor_update(text_sensor::TextSensor *obj, const std::string &state) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_text_sensor_state(obj);
}
#endif

#ifdef USE_CLIMATE
void APIServer::on_climate_update(climate::Climate *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_climate_state(obj);
}
#endif

#ifdef USE_NUMBER
void APIServer::on_number_update(number::Number *obj, float state) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_number_state(obj);
}
#endif

#ifdef USE_DATETIME_DATE
void APIServer::on_date_update(datetime::DateEntity *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_date_state(obj);
}
#endif

#ifdef USE_DATETIME_TIME
void APIServer::on_time_update(datetime::TimeEntity *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_time_state(obj);
}
#endif

#ifdef USE_DATETIME_DATETIME
void APIServer::on_datetime_update(datetime::DateTimeEntity *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_datetime_state(obj);
}
#endif

#ifdef USE_TEXT
void APIServer::on_text_update(text::Text *obj, const std::string &state) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_text_state(obj);
}
#endif

#ifdef USE_SELECT
void APIServer::on_select_update(select::Select *obj, const std::string &state, size_t index) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_select_state(obj);
}
#endif

#ifdef USE_LOCK
void APIServer::on_lock_update(lock::Lock *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_lock_state(obj);
}
#endif

#ifdef USE_VALVE
void APIServer::on_valve_update(valve::Valve *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_valve_state(obj);
}
#endif

#ifdef USE_MEDIA_PLAYER
void APIServer::on_media_player_update(media_player::MediaPlayer *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_media_player_state(obj);
}
#endif

#ifdef USE_EVENT
void APIServer::on_event(event::Event *obj, const std::string &event_type) {
  for (auto &c : this->clients_)
    c->send_event(obj, event_type);
}
#endif

#ifdef USE_UPDATE
void APIServer::on_update(update::UpdateEntity *obj) {
  for (auto &c : this->clients_)
    c->send_update_state(obj);
}
#endif

#ifdef USE_ALARM_CONTROL_PANEL
void APIServer::on_alarm_control_panel_update(alarm_control_panel::AlarmControlPanel *obj) {
  if (obj->is_internal())
    return;
  for (auto &c : this->clients_)
    c->send_alarm_control_panel_state(obj);
}
#endif

float APIServer::get_setup_priority() const { return setup_priority::AFTER_WIFI; }

void APIServer::set_port(uint16_t port) { this->port_ = port; }

#ifdef USE_API_PASSWORD
void APIServer::set_password(const std::string &password) { this->password_ = password; }
#endif

void APIServer::set_batch_delay(uint16_t batch_delay) { this->batch_delay_ = batch_delay; }

void APIServer::send_homeassistant_service_call(const HomeassistantServiceResponse &call) {
  for (auto &client : this->clients_) {
    client->send_homeassistant_service_call(call);
  }
}

void APIServer::subscribe_home_assistant_state(std::string entity_id, optional<std::string> attribute,
                                               std::function<void(std::string)> f) {
  this->state_subs_.push_back(HomeAssistantStateSubscription{
      .entity_id = std::move(entity_id),
      .attribute = std::move(attribute),
      .callback = std::move(f),
      .once = false,
  });
}

void APIServer::get_home_assistant_state(std::string entity_id, optional<std::string> attribute,
                                         std::function<void(std::string)> f) {
  this->state_subs_.push_back(HomeAssistantStateSubscription{
      .entity_id = std::move(entity_id),
      .attribute = std::move(attribute),
      .callback = std::move(f),
      .once = true,
  });
};

const std::vector<APIServer::HomeAssistantStateSubscription> &APIServer::get_state_subs() const {
  return this->state_subs_;
}

uint16_t APIServer::get_port() const { return this->port_; }

void APIServer::set_reboot_timeout(uint32_t reboot_timeout) { this->reboot_timeout_ = reboot_timeout; }

#ifdef USE_API_NOISE
bool APIServer::save_noise_psk(psk_t psk, bool make_active) {
  auto &old_psk = this->noise_ctx_->get_psk();
  if (std::equal(old_psk.begin(), old_psk.end(), psk.begin())) {
    ESP_LOGW(TAG, "New PSK matches old");
    return true;
  }

  SavedNoisePsk new_saved_psk{psk};
  if (!this->noise_pref_.save(&new_saved_psk)) {
    ESP_LOGW(TAG, "Failed to save Noise PSK");
    return false;
  }
  // ensure it's written immediately
  if (!global_preferences->sync()) {
    ESP_LOGW(TAG, "Failed to sync preferences");
    return false;
  }
  ESP_LOGD(TAG, "Noise PSK saved");
  if (make_active) {
    this->set_timeout(100, [this, psk]() {
      ESP_LOGW(TAG, "Disconnecting all clients to reset connections");
      this->set_noise_psk(psk);
      for (auto &c : this->clients_) {
        c->send_message(DisconnectRequest());
      }
    });
  }
  return true;
}
#endif

#ifdef USE_HOMEASSISTANT_TIME
void APIServer::request_time() {
  for (auto &client : this->clients_) {
    if (!client->flags_.remove && client->is_authenticated())
      client->send_time_request();
  }
}
#endif

bool APIServer::is_connected() const { return !this->clients_.empty(); }

void APIServer::on_shutdown() {
  this->shutting_down_ = true;

  // Close the listening socket to prevent new connections
  if (this->socket_) {
    this->socket_->close();
    this->socket_ = nullptr;
  }

  // Change batch delay to 5ms for quick flushing during shutdown
  this->batch_delay_ = 5;

  // Send disconnect requests to all connected clients
  for (auto &c : this->clients_) {
    if (!c->send_message(DisconnectRequest())) {
      // If we can't send the disconnect request directly (tx_buffer full),
      // schedule it at the front of the batch so it will be sent with priority
      c->schedule_message_front_(nullptr, &APIConnection::try_send_disconnect_request, DisconnectRequest::MESSAGE_TYPE);
    }
  }
}

bool APIServer::teardown() {
  // If network is disconnected, no point trying to flush buffers
  if (!network::is_connected()) {
    return true;
  }
  this->loop();

  // Return true only when all clients have been torn down
  return this->clients_.empty();
}

}  // namespace api
}  // namespace esphome
#endif
