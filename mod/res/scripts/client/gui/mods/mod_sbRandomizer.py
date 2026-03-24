import os
import random
import zipfile
import shutil
import BigWorld
from gui.modsSettingsApi import g_modsSettingsApi, templates

try:
    from PlayerEvents import g_playerEvents
except Exception as e:
    print('[SBRandomizer] ERROR importing PlayerEvents: {}'.format(e))

try:
    from Avatar import PlayerAvatar
except Exception as e:
    print('[SBRandomizer] ERROR importing Avatar: {}'.format(e))

MOD_LINKAGE = 'skybox_randomizer'
MOD_DATA_VERSION = 1

class SkyboxRandomizer:
    def __init__(self):
        try:
            self.mods_path = None
            self.res_mods_path = None
            self.sky_packs_path = './mods/configs/sbr_Packs/'
            self.manifest_path = './mods/configs/sbr_Packs/.sbr_manifest.json'
            self.available_packs = []
            self.current_pack = None
            self.installed_pack = None
            self.pack_history = []
            self.tracked_files = []
            self.initialized = False
            self.in_battle = False
            self.pending_swap_callback = None
            self.waiting_for_hangar_gui = False
            self.pack_to_install = None
            self.settings = {}
            
            self._register_events()
            
        except Exception as e:
            print('[SBRandomizer] ERROR during initialization: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _get_game_version(self):
        try:
            import game
            if hasattr(game, 'GameParams') and hasattr(game.GameParams, 'version'):
                return game.GameParams.version
        except:
            pass
        
        try:
            mods_path = './mods/'
            if os.path.exists(mods_path):
                all_dirs = os.listdir(mods_path)
                version_dirs = []
                for d in all_dirs:
                    full_path = os.path.join(mods_path, d)
                    if not os.path.isdir(full_path):
                        continue
                    if d.replace('.', '').replace('_', '').isdigit() and d.count('.') >= 2:
                        version_dirs.append(d)
                
                if version_dirs:
                    version_dirs.sort(reverse=True)
                    return version_dirs[0]
        except:
            pass
        
        return None
    
    def _scan_available_packs(self):
        try:
            if not os.path.exists(self.sky_packs_path):
                return

            self.available_packs = ['Default']
            
            for item in os.listdir(self.sky_packs_path):
                if item.endswith('.wotmod'):
                    pack_name = os.path.splitext(item)[0]
                    self.available_packs.append(pack_name)

            packs_without_default = self.available_packs[1:]
            packs_without_default.sort()
            self.available_packs = ['Default'] + packs_without_default

        except Exception as e:
            print('[SBRandomizer] Error scanning packs: {}'.format(e))
    
    def _build_settings_template(self):
        try:
            column1 = []
            column2 = []
            
            pack_labels = [pack for pack in self.available_packs]
            dropdown = templates.createDropdown(
                'Manual Pack Selection',
                'manual_pack',
                pack_labels,
                0,
                tooltip='{HEADER}Manual Pack Selection{/HEADER}{BODY}Choose a specific pack to use when locked{/BODY}'
            )
            column1.append(dropdown)
            
            lock_checkbox = templates.createCheckbox(
                'Lock Selection (Disable Randomization)',
                'lock_selection',
                False,
                tooltip='{HEADER}Lock Selection{/HEADER}{BODY}When enabled, always use the manually selected pack instead of randomizing{/BODY}'
            )
            column1.append(lock_checkbox)
            
            for pack in self.available_packs:
                safe_name = pack.replace(' ', '_').replace('-', '_').replace('.', '_')
                default_enabled = False if pack == 'Default' else True
                
                checkbox = templates.createCheckbox(
                    pack,
                    'enable_{}'.format(safe_name),
                    default_enabled,
                    tooltip='{{HEADER}}Enable/Disable Pack{{/HEADER}}{{BODY}}Toggle whether "{}" can be randomly selected{{/BODY}}'.format(pack)
                )
                column2.append(checkbox)
                
                slider = templates.createSlider(
                    '  Weight',
                    'weight_{}'.format(safe_name),
                    1.0,
                    0.1,
                    5.0,
                    0.1
                )
                column2.append(slider)
            
            template = {
                'modDisplayName': 'Skybox Randomizer',
                'enabled': True,
                'column1': column1,
                'column2': column2
            }
            
            return template
            
        except Exception as e:
            print('[SBRandomizer] Error building template: {}'.format(e))
            import traceback
            traceback.print_exc()
            return None
    
    def _build_default_settings(self):
        settings = {
            'enabled': True,
            'manual_pack': 0,
            'lock_selection': False,
            'separator_1': False
        }
        
        for pack in self.available_packs:
            safe_name = pack.replace(' ', '_').replace('-', '_').replace('.', '_')
            settings['enable_{}'.format(safe_name)] = pack != 'Default'
            settings['weight_{}'.format(safe_name)] = 1.0
        
        return settings
    
    def _register_modsettings(self):
        try:
            if not self.available_packs:
                return
            
            template = self._build_settings_template()
            if not template:
                return
            
            savedSettings = g_modsSettingsApi.getModSettings(MOD_LINKAGE, template)
            
            if savedSettings:
                self.settings = savedSettings
                g_modsSettingsApi.registerCallback(MOD_LINKAGE, self._on_settings_changed, None)
            else:
                self.settings = self._build_default_settings()
                g_modsSettingsApi.setModTemplate(MOD_LINKAGE, template, self._on_settings_changed, None)
            
        except Exception as e:
            print('[SBRandomizer] Error registering ModSettingsAPI: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _on_settings_changed(self, linkage, newSettings):
        if linkage == MOD_LINKAGE:
            try:
                self.settings = newSettings
            except Exception as e:
                print('[SBRandomizer] Error in settings callback: {}'.format(e))
    
    def _get_enabled_packs(self):
        enabled = []
        for pack in self.available_packs:
            safe_name = pack.replace(' ', '_').replace('-', '_').replace('.', '_')
            if self.settings.get('enable_{}'.format(safe_name), True):
                enabled.append(pack)
        return enabled
    
    def _get_pack_weight(self, pack):
        safe_name = pack.replace(' ', '_').replace('-', '_').replace('.', '_')
        return self.settings.get('weight_{}'.format(safe_name), 1.0)
    
    def _get_manual_pack(self):
        pack_index = self.settings.get('manual_pack', 0)
        if 0 <= pack_index < len(self.available_packs):
            return self.available_packs[pack_index]
        return 'Default'
    
    def _is_selection_locked(self):
        return self.settings.get('lock_selection', False)
    
    def _select_weighted_pack(self, pack_list=None):
        if pack_list is None:
            pack_list = self._get_enabled_packs()
        
        if not pack_list:
            return None
        
        weights = []
        for pack in pack_list:
            weight = self._get_pack_weight(pack)
            weights.append(max(0.1, weight))
        
        total_weight = sum(weights)
        if total_weight <= 0:
            return random.choice(pack_list)
        
        rand_val = random.uniform(0, total_weight)
        cumulative = 0
        for pack, weight in zip(pack_list, weights):
            cumulative += weight
            if rand_val <= cumulative:
                return pack
        
        return pack_list[-1]
    
    def _complete_initialization(self):
        if self.initialized:
            return
        
        try:
            version = self._get_game_version()
            if not version:
                BigWorld.callback(1.0, self._complete_initialization)
                return
            
            self.mods_path = './mods/{}/'.format(version)
            self.res_mods_path = './res_mods/{}/'.format(version)
            
            if not os.path.exists(self.res_mods_path):
                os.makedirs(self.res_mods_path)
            
            # Clean only our tracked files from previous session (preserves other mods)
            self._cleanup_from_manifest()
            
            self._scan_available_packs()
            self._register_modsettings()

            if self.available_packs:
                if self._is_selection_locked():
                    self.current_pack = self._get_manual_pack()
                else:
                    enabled_packs = self._get_enabled_packs()
                    if enabled_packs:
                        self.current_pack = self._select_weighted_pack(enabled_packs)
                    else:
                        self.current_pack = 'Default'
                
                self.pack_history.append(self.current_pack)
                self._install_pack(self.current_pack)
            
            self.initialized = True
            
        except Exception as e:
            print('[SBRandomizer] ERROR during initialization: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _get_wotmod_path(self, pack_name):
        return os.path.join(self.sky_packs_path, '{}.wotmod'.format(pack_name))

    def _install_pack(self, pack_name):
        try:
            if pack_name == 'Default':
                self._uninstall_pack()
                self.installed_pack = 'Default'
                self._save_manifest()
                return
            
            wotmod_path = self._get_wotmod_path(pack_name)
            if not os.path.exists(wotmod_path):
                return

            self._uninstall_pack()
            self.tracked_files = []
            
            with zipfile.ZipFile(wotmod_path, 'r') as z:
                res_prefix = 'res/'
                files_installed = 0
                
                for zip_path in z.namelist():
                    if not zip_path.startswith(res_prefix):
                        continue

                    rel_path = zip_path[len(res_prefix):]
                    
                    if not rel_path or rel_path.endswith('/'):
                        continue
                    
                    dest_path = os.path.join(self.res_mods_path, rel_path)
                    dest_dir = os.path.dirname(dest_path)
                    
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    
                    top_level = rel_path.split('/')[0]
                    if top_level not in self.tracked_files:
                        self.tracked_files.append(top_level)
                    
                    with z.open(zip_path) as src, open(dest_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    
                    files_installed += 1

                self.installed_pack = pack_name
                self._save_manifest()
                
        except zipfile.BadZipFile:
            print('[SBRandomizer] ERROR: "{}" is not a valid wotmod file'.format(pack_name))
        except Exception as e:
            print('[SBRandomizer] ERROR installing pack: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _save_manifest(self):
        """Save the current tracked files to a manifest file for persistence between sessions"""
        try:
            import json
            manifest_data = {
                'version': self._get_game_version(),
                'tracked_files': self.tracked_files,
                'installed_pack': self.installed_pack
            }
            
            with open(self.manifest_path, 'w') as f:
                json.dump(manifest_data, f, indent=2)
                
        except Exception as e:
            print('[SBRandomizer] Error saving manifest: {}'.format(e))
    
    def _load_manifest(self):
        """Load tracked files from previous session's manifest"""
        try:
            import json
            if not os.path.exists(self.manifest_path):
                return None
            
            with open(self.manifest_path, 'r') as f:
                manifest_data = json.load(f)
            
            # Only use manifest if it's for the same game version
            current_version = self._get_game_version()
            if manifest_data.get('version') == current_version:
                return manifest_data
            else:
                print('[SBRandomizer] Manifest is for different game version, ignoring')
                return None
                
        except Exception as e:
            print('[SBRandomizer] Error loading manifest: {}'.format(e))
            return None
    
    def _cleanup_from_manifest(self):
        """Clean up files from a previous session using the saved manifest"""
        try:
            manifest = self._load_manifest()
            if not manifest or not manifest.get('tracked_files'):
                print('[SBRandomizer] No manifest found or no tracked files to clean')
                return
            
            if not os.path.exists(self.res_mods_path):
                return
            
            print('[SBRandomizer] Cleaning up {} items from previous session...'.format(
                len(manifest['tracked_files'])))
            
            for item in manifest['tracked_files']:
                item_path = os.path.join(self.res_mods_path, item)
                if not os.path.exists(item_path):
                    continue
                    
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    print('[SBRandomizer] Removed: {}'.format(item))
                except Exception as e:
                    print('[SBRandomizer] Could not remove {}: {}'.format(item, e))
            
            print('[SBRandomizer] Cleanup from manifest complete')
            
        except Exception as e:
            print('[SBRandomizer] ERROR during manifest cleanup: {}'.format(e))
    
    def _cleanup_res_mods_full(self):
        """Perform a full cleanup of res_mods directory on startup to remove any leftover packs"""
        try:
            if not os.path.exists(self.res_mods_path):
                return
            
            print('[SBRandomizer] Performing startup cleanup of res_mods...')
            
            for item in os.listdir(self.res_mods_path):
                item_path = os.path.join(self.res_mods_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    print('[SBRandomizer] Could not remove {}: {}'.format(item, e))
            
            print('[SBRandomizer] Startup cleanup complete')
            
        except Exception as e:
            print('[SBRandomizer] ERROR during startup cleanup: {}'.format(e))
    
    def _uninstall_pack(self):
        try:
            if not os.path.exists(self.res_mods_path):
                return
            
            # Only remove tracked files/directories installed by this mod
            for item in self.tracked_files:
                item_path = os.path.join(self.res_mods_path, item)
                if not os.path.exists(item_path):
                    continue
                    
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    print('[SBRandomizer] Could not remove {}: {}'.format(item, e))
            
            self.installed_pack = None
            self.tracked_files = []
            self._save_manifest()
            
        except Exception as e:
            print('[SBRandomizer] ERROR cleaning res_mods: {}'.format(e))
    
    def _register_events(self):
        try:
            g_playerEvents.onAccountBecomePlayer += self._on_account_ready
            g_playerEvents.onAccountShowGUI += self._on_hangar_gui_ready
        except Exception as e:
            print('[SBRandomizer] ERROR registering events: {}'.format(e))
    
    def _hook_avatar_events(self):
        try:
            original_onLeaveWorld = PlayerAvatar.onLeaveWorld
            original_onEnterWorld = PlayerAvatar.onEnterWorld
            
            def hooked_onLeaveWorld(self):
                g_skyboxRandomizer._on_battle_ended()
                return original_onLeaveWorld(self)
            
            def hooked_onEnterWorld(self, prereqs):
                g_skyboxRandomizer._on_battle_started()
                return original_onEnterWorld(self, prereqs)
            
            PlayerAvatar.onLeaveWorld = hooked_onLeaveWorld
            PlayerAvatar.onEnterWorld = hooked_onEnterWorld
            
        except Exception as e:
            print('[SBRandomizer] ERROR hooking avatar events: {}'.format(e))
    
    def _on_hangar_gui_ready(self, ctx):
        try:
            if self.waiting_for_hangar_gui and self.pack_to_install and not self.in_battle:
                self.waiting_for_hangar_gui = False
                BigWorld.callback(2.0, self._execute_pack_swap)
                
        except Exception as e:
            print('[SBRandomizer] ERROR in _on_hangar_gui_ready: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _execute_pack_swap(self):
        try:
            if self.in_battle or not self.pack_to_install:
                return
            
            self._install_pack(self.pack_to_install)
            self.pack_to_install = None
            
        except Exception as e:
            print('[SBRandomizer] ERROR in _execute_pack_swap: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _on_battle_started(self):
        self.in_battle = True
        
        if self.waiting_for_hangar_gui:
            self.waiting_for_hangar_gui = False
            self.pack_to_install = None
        
        if self.pending_swap_callback is not None:
            try:
                BigWorld.cancelCallback(self.pending_swap_callback)
            except:
                pass
            self.pending_swap_callback = None
    
    def _on_battle_ended(self):
        self.in_battle = False
        
        if not self.initialized:
            return
        
        try:
            if self._is_selection_locked():
                self.current_pack = self._get_manual_pack()
            else:
                enabled_packs = self._get_enabled_packs()
                
                if not enabled_packs:
                    self.current_pack = 'Default'
                else:
                    self.current_pack = self._select_weighted_pack(enabled_packs)
            
            self.pack_history.append(self.current_pack)
            if len(self.pack_history) > 10:
                self.pack_history.pop(0)
            
            self.waiting_for_hangar_gui = True
            self.pack_to_install = self.current_pack
            
        except Exception as e:
            print('[SBRandomizer] ERROR in _on_battle_ended: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _on_account_ready(self):
        if not self.initialized:
            self._complete_initialization()
            self._hook_avatar_events()

try:
    g_skyboxRandomizer = SkyboxRandomizer()
except Exception as e:
    print('[SBRandomizer] FATAL ERROR: {}'.format(e))
    import traceback
    traceback.print_exc()