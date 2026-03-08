import os
import random
import zipfile
import shutil
import BigWorld

try:
    from PlayerEvents import g_playerEvents
except Exception as e:
    print('[SBRandomizer] ERROR importing PlayerEvents: {}'.format(e))

try:
    from Avatar import PlayerAvatar
except Exception as e:
    print('[SBRandomizer] ERROR importing Avatar: {}'.format(e))

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

            if self.available_packs:
                
                self.current_pack = random.choice(self.available_packs)
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
            self.tracked_files = []  # Till later bud
            
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
            # Check if we're waiting to swap after a battle
            if self.waiting_for_hangar_gui and self.pack_to_install and not self.in_battle:
                print('[SBRandomizer] Hangar GUI ready event received')
                self.waiting_for_hangar_gui = False
                
                # Wait 2 more seconds for full stabilization before swapping files
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
        
        # Cancel any pending pack swap operations
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
        
        if not self.initialized or not self.available_packs:
            return
        
        try:
            if len(self.pack_history) >= 2 and self.pack_history[-1] == self.pack_history[-2]:
                available_choices = [p for p in self.available_packs if p != self.pack_history[-1]]
                if available_choices:
                    self.current_pack = random.choice(available_choices)
                else:
                    self.current_pack = random.choice(self.available_packs)
            else:
                self.current_pack = random.choice(self.available_packs)
            
            self.pack_history.append(self.current_pack)
            if len(self.pack_history) > 10:
                self.pack_history.pop(0)
            
            print('[SBRandomizer] Next battle will use: {}'.format(self.current_pack))
            
            # Set flag to wait for hangar GUI ready event
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