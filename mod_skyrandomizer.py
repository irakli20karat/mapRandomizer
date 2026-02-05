import os
import shutil
import random
import BigWorld
import ResMgr

print('[SkyRandomizer] ===== MOD LOADING =====')

try:
    from PlayerEvents import g_playerEvents
    print('[SkyRandomizer] PlayerEvents imported successfully')
except Exception as e:
    print('[SkyRandomizer] ERROR importing PlayerEvents: {}'.format(e))

class SkyboxRandomizer:
    def __init__(self):
        print('[SkyRandomizer] Initializing SkyboxRandomizer...')
        try:
            self.skybox_packs_path = './mods/skyPacks/'
            self.res_mods_path = None
            self.available_packs = []
            self.current_pack = None
            self.installed_wotmod = None
            self.initialized = False
            
            print('[SkyRandomizer] Source path: {}'.format(self.skybox_packs_path))
            
            self._register_events()
            
            print('[SkyRandomizer] Waiting for game to fully load...')
        except Exception as e:
            print('[SkyRandomizer] ERROR during initialization: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _get_game_version(self):
        """Safely get game version"""
        try:
            import game
            if hasattr(game, 'GameParams') and hasattr(game.GameParams, 'version'):
                version = game.GameParams.version
                print('[SkyRandomizer] Got version from GameParams: {}'.format(version))
                return version
        except Exception as e:
            print('[SkyRandomizer] Could not get version from GameParams: {}'.format(e))
        
        try:
            res_mods_path = './res_mods/'
            print('[SkyRandomizer] Scanning {} for version folders...'.format(res_mods_path))
            
            if os.path.exists(res_mods_path):
                all_dirs = os.listdir(res_mods_path)
                print('[SkyRandomizer] Found directories: {}'.format(all_dirs))
                
                # Filter for version-like directories (X.X.X format with numbers and dots only)
                version_dirs = []
                for d in all_dirs:
                    if not os.path.isdir(os.path.join(res_mods_path, d)):
                        continue
                    if d.replace('.', '').replace('_', '').isdigit() and d.count('.') >= 2:
                        version_dirs.append(d)
                        print('[SkyRandomizer]   Valid version folder: {}'.format(d))
                    else:
                        print('[SkyRandomizer]   Skipping non-version folder: {}'.format(d))
                
                if version_dirs:
                    version_dirs.sort(reverse=True)
                    selected_version = version_dirs[0]
                    print('[SkyRandomizer] Selected version: {}'.format(selected_version))
                    return selected_version
                else:
                    print('[SkyRandomizer] No valid version folders found')
        except Exception as e:
            print('[SkyRandomizer] Error scanning for version: {}'.format(e))
            import traceback
            traceback.print_exc()
        
        return None
    
    def _complete_initialization(self):
        """Complete initialization once game is ready"""
        if self.initialized:
            return
        
        try:
            version = self._get_game_version()
            if not version:
                print('[SkyRandomizer] Could not determine game version, retrying in 1 second...')
                BigWorld.callback(1.0, self._complete_initialization)
                return
            
            print('[SkyRandomizer] ========================================')
            print('[SkyRandomizer] Game version: {}'.format(version))
            self.res_mods_path = './res_mods/{}/'.format(version)
            print('[SkyRandomizer] Res_mods directory: {}'.format(self.res_mods_path))
            print('[SkyRandomizer] Skybox packs directory: {}'.format(self.skybox_packs_path))
            print('[SkyRandomizer] ========================================')
            
            self._scan_available_packs()
            
            if self.available_packs:
                print('[SkyRandomizer] Installing initial skybox pack...')
                self._swap_skybox()
            else:
                print('[SkyRandomizer] ============================================')
                print('[SkyRandomizer] WARNING: No .wotmod files found!')
                print('[SkyRandomizer] Expected location: {}'.format(self.skybox_packs_path))
                print('[SkyRandomizer] Please place skybox .wotmod files there')
                print('[SkyRandomizer] ============================================')
            
            self.initialized = True
            print('[SkyRandomizer] Initialization complete!')
            
        except Exception as e:
            print('[SkyRandomizer] ERROR during delayed initialization: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _scan_available_packs(self):
        """Scan for available .wotmod files"""
        try:
            print('[SkyRandomizer] Scanning for skybox packs in: {}'.format(self.skybox_packs_path))
            
            if not os.path.exists(self.skybox_packs_path):
                print('[SkyRandomizer] Directory does not exist, creating: {}'.format(self.skybox_packs_path))
                os.makedirs(self.skybox_packs_path)
                print('[SkyRandomizer] Please place skybox .wotmod files in this directory')
                return
            
            all_files = os.listdir(self.skybox_packs_path)
            print('[SkyRandomizer] Files in directory: {}'.format(all_files))
            
            self.available_packs = [f for f in all_files if f.endswith('.wotmod')]
            
            if self.available_packs:
                print('[SkyRandomizer] Found {} skybox packs:'.format(len(self.available_packs)))
                for pack in self.available_packs:
                    print('[SkyRandomizer]   - {}'.format(pack))
            else:
                print('[SkyRandomizer] No .wotmod files found')
                
        except Exception as e:
            print('[SkyRandomizer] Error scanning packs: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _register_events(self):
        """Register game events"""
        try:
            g_playerEvents.onAccountBecomePlayer += self._on_account_ready
            g_playerEvents.onAvatarBecomeNonPlayer += self._on_leave_battle
            print('[SkyRandomizer] Events registered successfully')
        except Exception as e:
            print('[SkyRandomizer] ERROR registering events: {}'.format(e))
    
    def _on_leave_battle(self):
        """Called when leaving battle and returning to garage"""
        if not self.initialized:
            return
        
        print('[SkyRandomizer] Left battle, scheduling skybox swap...')
        BigWorld.callback(0.5, self._swap_skybox)
    
    def _on_account_ready(self):
        """Called when account becomes player (garage loaded)"""
        if not self.initialized:
            print('[SkyRandomizer] Account ready, completing initialization...')
            self._complete_initialization()
        else:
            print('[SkyRandomizer] Returned to garage')
    
    def _cleanup_previous_install(self):
        """Remove all skyPacks .wotmod files from res_mods and mods folders"""
        try:
            cleaned_files = []
            
            pack_names = set(self.available_packs)
            
            if self.res_mods_path and os.path.exists(self.res_mods_path):
                try:
                    for filename in os.listdir(self.res_mods_path):
                        if filename.endswith('.wotmod') and filename in pack_names:
                            file_path = os.path.join(self.res_mods_path, filename)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                                cleaned_files.append('res_mods: {}'.format(filename))
                except Exception as e:
                    print('[SkyRandomizer] Error cleaning res_mods: {}'.format(e))
            
            version = self._get_game_version()
            if version:
                mods_path = './mods/{}/'.format(version)
                if os.path.exists(mods_path):
                    try:
                        for filename in os.listdir(mods_path):
                            if filename.endswith('.wotmod') and filename in pack_names:
                                file_path = os.path.join(mods_path, filename)
                                if os.path.isfile(file_path):
                                    os.remove(file_path)
                                    cleaned_files.append('mods: {}'.format(filename))
                    except Exception as e:
                        print('[SkyRandomizer] Error cleaning mods: {}'.format(e))
            
            if cleaned_files:
                print('[SkyRandomizer] Cleaned up old packs:')
                for cleaned in cleaned_files:
                    print('[SkyRandomizer]   - {}'.format(cleaned))
            
            self.installed_wotmod = None
            
        except Exception as e:
            print('[SkyRandomizer] Error during cleanup: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _swap_skybox(self):
        """Randomly select and copy a .wotmod to res_mods folder"""
        if not self.initialized or not self.res_mods_path:
            print('[SkyRandomizer] Not initialized yet, cannot swap')
            return
        
        if not self.available_packs:
            print('[SkyRandomizer] No skybox packs available to swap')
            return
        
        try:
            selected_pack = random.choice(self.available_packs)
            
            if selected_pack == self.current_pack and len(self.available_packs) > 1:
                other_packs = [p for p in self.available_packs if p != self.current_pack]
                selected_pack = random.choice(other_packs)
            
            print('[SkyRandomizer] ===== SWAPPING SKYBOX =====')
            print('[SkyRandomizer] Selected: {}'.format(selected_pack))
            
            self._cleanup_previous_install()
            
            source = os.path.join(self.skybox_packs_path, selected_pack)
            destination = os.path.join(self.res_mods_path, selected_pack)
            
            print('[SkyRandomizer] Copying from: {}'.format(source))
            print('[SkyRandomizer] Copying to: {}'.format(destination))
            
            shutil.copy2(source, destination)
            print('[SkyRandomizer] File copied successfully')
            
            try:
                ResMgr.purge(self.res_mods_path)
                print('[SkyRandomizer] Resource cache purged')
            except Exception as e:
                print('[SkyRandomizer] Cache purge warning: {}'.format(e))
            
            self.current_pack = selected_pack
            self.installed_wotmod = selected_pack
            
            print('[SkyRandomizer] ===== SWAP COMPLETE =====')
            print('[SkyRandomizer] Active pack: {}'.format(selected_pack))
            print('[SkyRandomizer] Changes will apply on next map load')
            
        except Exception as e:
            print('[SkyRandomizer] ===== SWAP FAILED =====')
            print('[SkyRandomizer] Error: {}'.format(e))
            import traceback
            traceback.print_exc()

print('[SkyRandomizer] Creating mod instance...')
try:
    g_skyboxRandomizer = SkyboxRandomizer()
    print('[SkyRandomizer] ===== MOD LOADED SUCCESSFULLY =====')
except Exception as e:
    print('[SkyRandomizer] ===== FATAL ERROR =====')
    print('[SkyRandomizer] Failed to initialize: {}'.format(e))
    import traceback
    traceback.print_exc()