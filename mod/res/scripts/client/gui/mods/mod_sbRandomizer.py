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

# ModSettingsAPI configuration
MOD_LINKAGE = 'skybox_randomizer'
MOD_DATA_VERSION = 1

class SkyboxRandomizer:
    def __init__(self):
        try:
            self.mods_path = None
            self.res_mods_path = None
            self.sky_packs_path = './mods/sbr_Packs/'
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
            
            # Settings storage
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
                print('[SBRandomizer] Packs folder not found: {}'.format(self.sky_packs_path))
                return

            self.available_packs = []
            for item in os.listdir(self.sky_packs_path):
                if item.endswith('.wotmod'):
                    pack_name = os.path.splitext(item)[0]
                    self.available_packs.append(pack_name)

            self.available_packs.sort()
            print('[SBRandomizer] Found {} pack(s): {}'.format(
                len(self.available_packs), ', '.join(self.available_packs)))

        except Exception as e:
            print('[SBRandomizer] Error scanning packs: {}'.format(e))
    
    def _build_settings_template(self):
        """Build ModSettingsAPI template dynamically based on discovered packs"""
        try:
            column1 = []
            column2 = []
            
            # Split packs between two columns for better UI
            half = (len(self.available_packs) + 1) // 2
            
            for idx, pack in enumerate(self.available_packs):
                # Sanitize pack name for varName (no spaces, special chars)
                safe_name = pack.replace(' ', '_').replace('-', '_').replace('.', '_')
                
                # Checkbox to enable/disable pack
                checkbox = templates.createCheckbox(
                    pack,                              # text
                    'enable_{}'.format(safe_name),     # varName
                    True,                              # value
                    tooltip='{{HEADER}}Enable/Disable Pack{{/HEADER}}{{BODY}}Toggle whether "{}" can be selected for battles{{/BODY}}'.format(pack)
                )
                
                # Slider for weight (0.1 to 5.0)
                slider = templates.createSlider(
                    '  Weight',                        # text
                    'weight_{}'.format(safe_name),     # varName
                    1.0,                                # value
                    0.1,                                # minimum
                    5.0,                                # maximum
                    0.1                                 # snapInterval
                )
                
                # Add to appropriate column
                if idx < half:
                    column1.append(checkbox)
                    column1.append(slider)
                else:
                    column2.append(checkbox)
                    column2.append(slider)
            
            # Build template
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
        """Build default settings dict for all packs"""
        settings = {'enabled': True}
        
        for pack in self.available_packs:
            safe_name = pack.replace(' ', '_').replace('-', '_').replace('.', '_')
            settings['enable_{}'.format(safe_name)] = True
            settings['weight_{}'.format(safe_name)] = 1.0
        
        return settings
    
    def _register_modsettings(self):
        """Register mod with ModSettingsAPI"""
        try:
            if not self.available_packs:
                print('[SBRandomizer] No packs found, skipping ModSettingsAPI registration')
                return
            
            template = self._build_settings_template()
            if not template:
                print('[SBRandomizer] Failed to build settings template')
                return
            
            # Try to load saved settings
            savedSettings = g_modsSettingsApi.getModSettings(MOD_LINKAGE, template)
            
            if savedSettings:
                self.settings = savedSettings
                print('[SBRandomizer] Loaded saved settings from ModSettingsAPI')
                g_modsSettingsApi.registerCallback(MOD_LINKAGE, self._on_settings_changed, None)
            else:
                # First time - create default settings
                self.settings = self._build_default_settings()
                g_modsSettingsApi.setModTemplate(MOD_LINKAGE, template, self._on_settings_changed, None)
                print('[SBRandomizer] Registered new mod template with ModSettingsAPI')
            
        except Exception as e:
            print('[SBRandomizer] Error registering ModSettingsAPI: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _on_settings_changed(self, linkage, newSettings):
        """Callback when user changes settings in the menu"""
        if linkage == MOD_LINKAGE:
            try:
                print('[SBRandomizer] Settings changed: {}'.format(newSettings))
                self.settings = newSettings
            except Exception as e:
                print('[SBRandomizer] Error in settings callback: {}'.format(e))
    
    def _get_enabled_packs(self):
        """Get list of enabled packs from settings"""
        enabled = []
        for pack in self.available_packs:
            safe_name = pack.replace(' ', '_').replace('-', '_').replace('.', '_')
            if self.settings.get('enable_{}'.format(safe_name), True):
                enabled.append(pack)
        return enabled
    
    def _get_pack_weight(self, pack):
        """Get weight for a specific pack"""
        safe_name = pack.replace(' ', '_').replace('-', '_').replace('.', '_')
        return self.settings.get('weight_{}'.format(safe_name), 1.0)
    
    def _select_weighted_pack(self, pack_list=None):
        """Select a pack using weighted random selection"""
        if pack_list is None:
            pack_list = self._get_enabled_packs()
        
        if not pack_list:
            print('[SBRandomizer] No enabled packs available!')
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
            
            self._scan_available_packs()
            
            # Register with ModSettingsAPI
            self._register_modsettings()

            if self.available_packs:
                enabled_packs = self._get_enabled_packs()
                if enabled_packs:
                    self.current_pack = self._select_weighted_pack(enabled_packs)
                    self.pack_history.append(self.current_pack)
                    self._install_pack(self.current_pack)
                else:
                    print('[SBRandomizer] WARNING: No packs enabled in settings!')
            
            self.initialized = True
            
        except Exception as e:
            print('[SBRandomizer] ERROR during initialization: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _get_wotmod_path(self, pack_name):
        return os.path.join(self.sky_packs_path, '{}.wotmod'.format(pack_name))

    def _install_pack(self, pack_name):
        try:
            wotmod_path = self._get_wotmod_path(pack_name)
            if not os.path.exists(wotmod_path):
                print('[SBRandomizer] ERROR: Pack file not found: {}'.format(wotmod_path))
                return

            print('[SBRandomizer] Installing: {}'.format(pack_name))
            
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
                
                if files_installed == 0:
                    print('[SBRandomizer] Pack "{}" is empty - using default sky'.format(pack_name))
                else:
                    print('[SBRandomizer] Installed {} file(s) from pack: {}'.format(files_installed, pack_name))

                self.installed_pack = pack_name
                
        except zipfile.BadZipFile:
            print('[SBRandomizer] ERROR: "{}" is not a valid wotmod file'.format(pack_name))
        except Exception as e:
            print('[SBRandomizer] ERROR installing pack: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _uninstall_pack(self):
        try:
            if not os.path.exists(self.res_mods_path):
                return
            
            print('[SBRandomizer] Cleaning res_mods...')
            
            for item in os.listdir(self.res_mods_path):
                item_path = os.path.join(self.res_mods_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    print('[SBRandomizer] Could not remove {}: {}'.format(item, e))
            
            self.installed_pack = None
            self.tracked_files = []
            
        except Exception as e:
            print('[SBRandomizer] ERROR cleaning res_mods: {}'.format(e))
    
    def _register_events(self):
        try:
            g_playerEvents.onAccountBecomePlayer += self._on_account_ready
            g_playerEvents.onAccountShowGUI += self._on_hangar_gui_ready
            print('[SBRandomizer] Subscribed to player events')
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
                print('[SBRandomizer] Hangar GUI ready event received')
                self.waiting_for_hangar_gui = False
                
                print('[SBRandomizer] Waiting 2 seconds for stabilization...')
                BigWorld.callback(2.0, self._execute_pack_swap)
                
        except Exception as e:
            print('[SBRandomizer] ERROR in _on_hangar_gui_ready: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _execute_pack_swap(self):
        try:
            if self.in_battle or not self.pack_to_install:
                print('[SBRandomizer] Skipping pack swap - in_battle={}, pack={}'.format(
                    self.in_battle, self.pack_to_install))
                return
            
            print('[SBRandomizer] Executing pack swap for: {}'.format(self.pack_to_install))
            self._install_pack(self.pack_to_install)
            self.pack_to_install = None
            print('[SBRandomizer] Pack swap complete, ready for next battle')
            
        except Exception as e:
            print('[SBRandomizer] ERROR in _execute_pack_swap: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _on_battle_started(self):
        self.in_battle = True
        
        if self.waiting_for_hangar_gui:
            print('[SBRandomizer] Battle started - cancelling pending pack swap')
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
            enabled_packs = self._get_enabled_packs()
            
            if not enabled_packs:
                print('[SBRandomizer] No enabled packs - skipping selection')
                return
            
            self.current_pack = self._select_weighted_pack(enabled_packs)
            
            self.pack_history.append(self.current_pack)
            if len(self.pack_history) > 10:
                self.pack_history.pop(0)
            
            weight = self._get_pack_weight(self.current_pack)
            print('[SBRandomizer] Next battle will use: {} (weight: {:.1f}x)'.format(
                self.current_pack, weight))
            
            self.waiting_for_hangar_gui = True
            self.pack_to_install = self.current_pack
            print('[SBRandomizer] Waiting for hangar GUI ready event...')
            
        except Exception as e:
            print('[SBRandomizer] ERROR in _on_battle_ended: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _on_account_ready(self):
        if not self.initialized:
            self._complete_initialization()
            self._hook_avatar_events()
            print('[SBRandomizer] Ready!')

print('[SBRandomizer] Loading...')
try:
    g_skyboxRandomizer = SkyboxRandomizer()
except Exception as e:
    print('[SBRandomizer] FATAL ERROR: {}'.format(e))
    import traceback
    traceback.print_exc()