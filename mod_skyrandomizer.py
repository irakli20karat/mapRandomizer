"""
SkyRandomizer - Randomizes skybox for each battle
"""

import os
import random
import zipfile
import shutil
import BigWorld

try:
    from PlayerEvents import g_playerEvents
except Exception as e:
    print('[SkyRandomizer] ERROR importing PlayerEvents: {}'.format(e))

try:
    from Avatar import PlayerAvatar
except Exception as e:
    print('[SkyRandomizer] ERROR importing Avatar: {}'.format(e))

class SkyboxRandomizer:
    def __init__(self):
        try:
            self.combined_wotmod_name = 'skyRandomizer_AllPacks.7z'
            self.mods_path = None
            self.res_mods_path = None
            self.sky_packs_path = './mods/skyPacks/'
            self.available_packs = []
            self.current_pack = None
            self.installed_pack = None
            self.pack_history = []
            self.initialized = False
            
            self._register_events()
            
        except Exception as e:
            print('[SkyRandomizer] ERROR during initialization: {}'.format(e))
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
    
    def _generate_combined_archive(self):
        try:
            if not os.path.exists(self.sky_packs_path):
                return False
            
            combined_path = os.path.join(self.sky_packs_path, self.combined_wotmod_name)
            
            wotmod_files = []
            for item in os.listdir(self.sky_packs_path):
                if item.endswith('.wotmod') and item != self.combined_wotmod_name:
                    wotmod_files.append(item)
            
            if not wotmod_files:
                return False
            
            print('[SkyRandomizer] Generating combined archive from {} packs...'.format(len(wotmod_files)))
            
            with zipfile.ZipFile(combined_path, 'w', zipfile.ZIP_DEFLATED) as out_zip:
                for wotmod_file in wotmod_files:
                    wotmod_path = os.path.join(self.sky_packs_path, wotmod_file)
                    pack_name = os.path.splitext(wotmod_file)[0]
                    
                    with zipfile.ZipFile(wotmod_path, 'r') as in_zip:
                        for file_info in in_zip.filelist:
                            if file_info.filename.endswith('/'):
                                continue
                            
                            new_path = os.path.join('spaces', pack_name, file_info.filename)
                            
                            file_data = in_zip.read(file_info.filename)
                            out_zip.writestr(new_path, file_data)
            
            print('[SkyRandomizer] Combined archive created')
            return True
            
        except Exception as e:
            print('[SkyRandomizer] ERROR generating combined archive: {}'.format(e))
            import traceback
            traceback.print_exc()
            return False
    
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
            
            combined_wotmod_path = os.path.join(self.sky_packs_path, self.combined_wotmod_name)
            
            if os.path.exists(combined_wotmod_path):
                os.remove(combined_wotmod_path)
            
            if not self._generate_combined_archive():
                return
            
            if os.path.exists(combined_wotmod_path):
                self._scan_available_packs_in_wotmod(combined_wotmod_path)
                
                if self.available_packs:
                    self.current_pack = random.choice(self.available_packs)
                    self.pack_history.append(self.current_pack)
                    print('[SkyRandomizer] Available packs: {}'.format(', '.join(self.available_packs)))
                    
                    self._install_pack(self.current_pack, combined_wotmod_path)
            
            self.initialized = True
            
        except Exception as e:
            print('[SkyRandomizer] ERROR during initialization: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _scan_available_packs_in_wotmod(self, wotmod_path):
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
        try:
            print('[SkyRandomizer] Installing: {}'.format(pack_name))
            
            if self.installed_pack:
                self._uninstall_pack()
            
            with zipfile.ZipFile(wotmod_path, 'r') as z:
                pack_prefix = 'spaces/{}/res/'.format(pack_name)
                files_installed = 0
                
                for zip_path in z.namelist():
                    if zip_path.startswith(pack_prefix):
                        rel_path = zip_path[len(pack_prefix):]
                        
                        if not rel_path or rel_path.endswith('/'):
                            continue
                        
                        dest_path = os.path.join(self.res_mods_path, rel_path)
                        dest_dir = os.path.dirname(dest_path)
                        
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir)
                        
                        with z.open(zip_path) as src, open(dest_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        
                        files_installed += 1
                
                self.installed_pack = pack_name
                
        except Exception as e:
            print('[SkyRandomizer] ERROR installing pack: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _uninstall_pack(self):
        try:
            if not self.installed_pack:
                return
            
            spaces_path = os.path.join(self.res_mods_path, 'spaces')
            if os.path.exists(spaces_path):
                for map_folder in os.listdir(spaces_path):
                    map_path = os.path.join(spaces_path, map_folder)
                    if os.path.isdir(map_path):
                        environments_path = os.path.join(map_path, 'environments')
                        if os.path.exists(environments_path):
                            shutil.rmtree(environments_path)
            
            self.installed_pack = None
            
        except Exception as e:
            print('[SkyRandomizer] ERROR uninstalling pack: {}'.format(e))
    
    def _register_events(self):
        try:
            g_playerEvents.onAccountBecomePlayer += self._on_account_ready
        except Exception as e:
            print('[SkyRandomizer] ERROR registering events: {}'.format(e))
    
    def _hook_avatar_destruction(self):
        try:
            original_onLeaveWorld = PlayerAvatar.onLeaveWorld
            
            def hooked_onLeaveWorld(self):
                g_skyboxRandomizer._on_battle_ended()
                return original_onLeaveWorld(self)
            
            PlayerAvatar.onLeaveWorld = hooked_onLeaveWorld
        except Exception as e:
            print('[SkyRandomizer] ERROR hooking avatar destruction: {}'.format(e))
    
    def _on_battle_ended(self):
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
            
            print('[SkyRandomizer] Next battle: {}'.format(self.current_pack))
            
            combined_wotmod_path = os.path.join(self.sky_packs_path, self.combined_wotmod_name)
            if os.path.exists(combined_wotmod_path):
                self._install_pack(self.current_pack, combined_wotmod_path)
            
        except Exception as e:
            print('[SkyRandomizer] ERROR in _on_battle_ended: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _on_account_ready(self):
        if not self.initialized:
            self._complete_initialization()
            self._hook_avatar_destruction()
            print('[SkyRandomizer] Ready!')

print('[SkyRandomizer] Loading...')
try:
    g_skyboxRandomizer = SkyboxRandomizer()
except Exception as e:
    print('[SkyRandomizer] FATAL ERROR: {}'.format(e))
    import traceback
    traceback.print_exc()