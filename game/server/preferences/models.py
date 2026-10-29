"""DTOs of the install preferences and first start (WEB-07.2)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from game.commands.preferences import (
    MAX_PORT,
    InstallPreferences,
    install_dir_problem,
    needs_first_start,
    saved_games_problem,
)


class InstallPreferencesJs(BaseModel):
    saved_game_dir: str
    dcs_install_dir: str
    prefer_liberation_payloads: bool
    setup_preferences_on_every_start: bool
    server_port: int = Field(ge=1, le=MAX_PORT)
    web_ui: bool

    class Config:
        title = "InstallPreferences"

    @staticmethod
    def from_preferences(preferences: InstallPreferences) -> InstallPreferencesJs:
        return InstallPreferencesJs(
            saved_game_dir=preferences.saved_game_dir,
            dcs_install_dir=preferences.dcs_install_dir,
            prefer_liberation_payloads=preferences.prefer_liberation_payloads,
            setup_preferences_on_every_start=(
                preferences.setup_preferences_on_every_start
            ),
            server_port=preferences.server_port,
            web_ui=preferences.web_ui,
        )

    def to_preferences(self) -> InstallPreferences:
        return InstallPreferences(
            saved_game_dir=self.saved_game_dir,
            dcs_install_dir=self.dcs_install_dir,
            prefer_liberation_payloads=self.prefer_liberation_payloads,
            setup_preferences_on_every_start=self.setup_preferences_on_every_start,
            server_port=self.server_port,
            web_ui=self.web_ui,
        )


class InstallPreferencesUpdateJs(InstallPreferencesJs):
    # Leaving the DCS installation folder empty needs this confirmation.
    allow_empty_install_dir: bool = False

    class Config:
        title = "InstallPreferencesUpdate"


class InstallPreferencesStateJs(BaseModel):
    """The saved preferences, what is wrong with them, and whether the first start
    setup must be shown."""

    preferences: InstallPreferencesJs
    first_start: bool
    saved_game_dir_problem: str | None
    dcs_install_dir_problem: str | None
    # Set after a save when MissionScripting.lua could not be replaced.
    warning: str | None = None

    class Config:
        title = "InstallPreferencesState"

    @staticmethod
    def from_preferences(
        preferences: InstallPreferences, warning: str | None = None
    ) -> InstallPreferencesStateJs:
        return InstallPreferencesStateJs(
            preferences=InstallPreferencesJs.from_preferences(preferences),
            first_start=needs_first_start(),
            saved_game_dir_problem=saved_games_problem(preferences.saved_game_dir),
            dcs_install_dir_problem=install_dir_problem(preferences.dcs_install_dir),
            warning=warning,
        )
