# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.util import RepeatedTimer
from octoprint.events import Events

class AutomaticshutdownPlugin(octoprint.plugin.TemplatePlugin,
							  octoprint.plugin.AssetPlugin,
							  octoprint.plugin.SimpleApiPlugin,
							  octoprint.plugin.EventHandlerPlugin,
							  octoprint.plugin.SettingsPlugin,
							  octoprint.plugin.StartupPlugin):

	def __init__(self):
		self._automatic_shutdown_enabled = False
		self._timeout_value = None
		self._timer = None

	def on_after_startup(self):
		self._logger.info("Automatic shutdown command: %s" % self._settings.get(["command"]))

	def get_assets(self):
		return dict(js=["js/automaticshutdown.js"])

	def get_template_configs(self):
		return [
			dict(type="sidebar",
				name="Automatic Shutdown",
				custom_bindings=False,
				icon="power-off"),
			dict(type="settings", custom_bindings=False),
		]

	def get_api_commands(self):
		return dict(enable=[],
			disable=[],
			abort=[])

	def get_settings_defaults(self):
		return dict(command="", delay=300)

	def on_api_command(self, command, data):
		import flask
		if command == "enable":
			self._automatic_shutdown_enabled = True
		elif command == "disable":
			self._automatic_shutdown_enabled = False
		elif command == "abort":
			if self._timer is not None:
				self._timer.cancel()
			self._logger.info("Shutdown aborted.")

	def on_event(self, event, payload):
		if event == Events.PRINT_STARTED:
			# Clear any existing timer (from aborted shutdown, or shutdown waiting to happen)
			if self._timer is not None:
				self._timer.cancel()
				self._timer = None
				self._plugin_manager.send_plugin_message(self._identifier, dict(type="timeout", timeout_value=-1))
		if event != Events.PRINT_DONE:
			return
		if not self._automatic_shutdown_enabled or not self._shutdown_command():
			return
		if self._timer is not None:
			return

		try:
			self._timeout_value = int(self._settings.get(["delay"]))
		except ValueError:
			self._logger.info("automaticshutdown: Invalid delay value, not shutting down")
			return

		self._timer = RepeatedTimer(1, self._timer_task)
		self._timer.start()
		self._plugin_manager.send_plugin_message(self._identifier, dict(type="timeout", timeout_value=self._timeout_value))

	def _shutdown_command(self):
		return self._settings.get(["command"])

	def _timer_task(self):
		self._timeout_value -= 1
		self._plugin_manager.send_plugin_message(self._identifier, dict(type="timeout", timeout_value=self._timeout_value))
		if self._timeout_value <= 0:
			self._timer.cancel()
			self._timer = None
			self._shutdown_system()

	def _shutdown_system(self):
		self._logger.info("Shutting down system with command: {command}".format(command=self._shutdown_command()))
		try:
			import sarge
			p = sarge.run(self._shutdown_command(), async=True)
		except Exception as e:
			self._logger.exception("Error when shutting down: {error}".format(error=e))
			return


__plugin_name__ = "Automatic Shutdown"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = AutomaticshutdownPlugin()

