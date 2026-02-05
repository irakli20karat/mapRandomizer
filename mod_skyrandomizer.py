"""
SkyRandomizer - FINAL SOLUTION
Install skybox files directly into res_mods to override base files
"""

import os
import random
import zipfile
import shutil
import BigWorld

print('[SkyRandomizer] ===== FINAL SOLUTION =====')

try:
    from PlayerEvents import g_playerEvents
    print('[SkyRandomizer] PlayerEvents imported')
except Exception as e:
    print('[SkyRandomizer] ERROR importing PlayerEvents: {}'.format(e))

try:
    from Avatar import PlayerAvatar
    print('[SkyRandomizer] Avatar imported')
except Exception as e:
    print('[SkyRandomizer] ERROR importing Avatar: {}'.format(e))

class SkyboxRandomizer:
    def __init__(self):
        print('[SkyRandomizer] Initializing...')
        try:
            self.combined_wotmod_name = 'skyRandomizer_AllPacks.7z'
            self.mods_path = None
            self.res_mods_path = None
            self.available_packs = []
            self.current_pack = None
            self.installed_pack = None
            self.initialized = False
            
            self._register_events()
            print('[SkyRandomizer] Events registered')
            
        except Exception as e:
            print('[SkyRandomizer] ERROR during initialization: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _get_game_version(self):
        """Get game version"""
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
    
    def _complete_initialization(self):
        """Complete initialization once game is ready"""
        if self.initialized:
            return
        
        try:
            version = self._get_game_version()
            if not version:
                BigWorld.callback(1.0, self._complete_initialization)
                return
            
            self.mods_path = './mods/{}/'.format(version)
            self.res_mods_path = './res_mods/{}/'.format(version)
            
            # Ensure res_mods directory exists
            if not os.path.exists(self.res_mods_path):
                os.makedirs(self.res_mods_path)
            
            # Check combined wotmod
            combined_wotmod_path = os.path.join(self.mods_path, self.combined_wotmod_name)
            if os.path.exists(combined_wotmod_path):
                self._scan_available_packs_in_wotmod(combined_wotmod_path)
                
                if self.available_packs:
                    self.current_pack = random.choice(self.available_packs)
                    print('[SkyRandomizer] Initial pack: {}'.format(self.current_pack))
                    print('[SkyRandomizer] Available packs: {}'.format(', '.join(self.available_packs)))
                    
                    # Install initial pack
                    self._install_pack(self.current_pack, combined_wotmod_path)
            else:
                print('[SkyRandomizer] WARNING: Combined wotmod not found at: {}'.format(combined_wotmod_path))
            
            self.initialized = True
            
        except Exception as e:
            print('[SkyRandomizer] ERROR during initialization: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _scan_available_packs_in_wotmod(self, wotmod_path):
        """Scan the combined wotmod to find available pack folders"""
        try:
            with zipfile.ZipFile(wotmod_path, 'r') as z:
                all_paths = z.namelist()
                pack_folders = set()
                for path in all_paths:
                    if path.startswith('spaces/'):
                        parts = path.split('/')
                        if len(parts) >= 2:
                            pack_folders.add(parts[1])
                
                self.available_packs = sorted(list(pack_folders))
                    
        except Exception as e:
            print('[SkyRandomizer] Error scanning wotmod: {}'.format(e))
    
    def _install_pack(self, pack_name, wotmod_path):
        """Install a pack's files into res_mods"""
        try:
            print('[SkyRandomizer] Installing pack: {}'.format(pack_name))
            
            # Remove old installation if exists
            if self.installed_pack:
                self._uninstall_pack()
            
            # Extract files from wotmod
            with zipfile.ZipFile(wotmod_path, 'r') as z:
                pack_prefix = 'spaces/{}/res/'.format(pack_name)
                files_installed = 0
                
                for zip_path in z.namelist():
                    if zip_path.startswith(pack_prefix):
                        # Get the path after the pack prefix
                        rel_path = zip_path[len(pack_prefix):]
                        
                        if not rel_path or rel_path.endswith('/'):
                            continue
                        
                        # Destination in res_mods
                        dest_path = os.path.join(self.res_mods_path, rel_path)
                        
                        # Create directories
                        dest_dir = os.path.dirname(dest_path)
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir)
                        
                        # Extract file
                        with z.open(zip_path) as src, open(dest_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        
                        files_installed += 1
                
                print('[SkyRandomizer] Installed {} files from {}'.format(files_installed, pack_name))
                self.installed_pack = pack_name
                
        except Exception as e:
            print('[SkyRandomizer] ERROR installing pack: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _uninstall_pack(self):
        """Remove installed pack files from res_mods"""
        try:
            if not self.installed_pack:
                return
            
            print('[SkyRandomizer] Uninstalling pack: {}'.format(self.installed_pack))
            
            # Remove all map environment folders from res_mods/spaces
            spaces_path = os.path.join(self.res_mods_path, 'spaces')
            if os.path.exists(spaces_path):
                for map_folder in os.listdir(spaces_path):
                    map_path = os.path.join(spaces_path, map_folder)
                    if os.path.isdir(map_path):
                        environments_path = os.path.join(map_path, 'environments')
                        if os.path.exists(environments_path):
                            shutil.rmtree(environments_path)
                            print('[SkyRandomizer] Removed: {}'.format(environments_path))
            
            self.installed_pack = None
            
        except Exception as e:
            print('[SkyRandomizer] ERROR uninstalling pack: {}'.format(e))
    
    def _register_events(self):
        """Register game events"""
        try:
            g_playerEvents.onAccountBecomePlayer += self._on_account_ready
        except Exception as e:
            print('[SkyRandomizer] ERROR registering events: {}'.format(e))
    
    def _hook_avatar_destruction(self):
        """Hook Avatar.onLeaveWorld to detect battle end"""
        try:
            original_onLeaveWorld = PlayerAvatar.onLeaveWorld
            
            def hooked_onLeaveWorld(self):
                g_skyboxRandomizer._on_battle_ended()
                return original_onLeaveWorld(self)
            
            PlayerAvatar.onLeaveWorld = hooked_onLeaveWorld
            print('[SkyRandomizer] Avatar destruction hook installed')
        except Exception as e:
            print('[SkyRandomizer] ERROR hooking avatar destruction: {}'.format(e))
    
    def _on_battle_ended(self):
        """Called when battle ends - select and install new skybox for next battle"""
        if not self.initialized or not self.available_packs:
            return
        
        try:
            # Select a different pack for the next battle
            if len(self.available_packs) > 1:
                other_packs = [p for p in self.available_packs if p != self.current_pack]
                self.current_pack = random.choice(other_packs)
            else:
                self.current_pack = self.available_packs[0]
            
            print('[SkyRandomizer] Next battle will use: {}'.format(self.current_pack))
            
            # Install the new pack
            combined_wotmod_path = os.path.join(self.mods_path, self.combined_wotmod_name)
            if os.path.exists(combined_wotmod_path):
                self._install_pack(self.current_pack, combined_wotmod_path)
                print('[SkyRandomizer] Pack {} installed and ready for next battle'.format(self.current_pack))
            
        except Exception as e:
            print('[SkyRandomizer] ERROR in _on_battle_ended: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _on_account_ready(self):
        """Called when account becomes player (garage loaded)"""
        if not self.initialized:
            self._complete_initialization()
            self._hook_avatar_destruction()
            print('[SkyRandomizer] Ready!')

print('[SkyRandomizer] Creating mod instance...')
try:
    g_skyboxRandomizer = SkyboxRandomizer()
    print('[SkyRandomizer] ===== LOADED =====')
except Exception as e:
    print('[SkyRandomizer] ===== FATAL ERROR =====')
    print('[SkyRandomizer] Failed to initialize: {}'.format(e))
    import traceback
    traceback.print_exc()