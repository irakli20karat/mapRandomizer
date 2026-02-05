import os
import shutil
import random
import zipfile
import tempfile
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
            self.mods_path = None  # Will be set to ./mods/{version}/
            self.hotswap_wotmod_name = 'skyrandomizerHotSwap.wotmod'
            self.hotswap_wotmod_path = None
            self.available_packs = []
            self.current_pack = None
            self.initialized = False
            
            print('[SkyRandomizer] Source path: {}'.format(self.skybox_packs_path))
            print('[SkyRandomizer] Strategy: Create hot-swappable wotmod in mods folder')
            
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
            mods_path = './mods/'
            print('[SkyRandomizer] Scanning {} for version folders...'.format(mods_path))
            
            if os.path.exists(mods_path):
                all_dirs = os.listdir(mods_path)
                print('[SkyRandomizer] Found directories: {}'.format(all_dirs))
                
                version_dirs = []
                for d in all_dirs:
                    full_path = os.path.join(mods_path, d)
                    if not os.path.isdir(full_path):
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
            self.mods_path = './mods/{}/'.format(version)
            self.hotswap_wotmod_path = os.path.join(self.mods_path, self.hotswap_wotmod_name)
            print('[SkyRandomizer] Mods directory: {}'.format(self.mods_path))
            print('[SkyRandomizer] HotSwap wotmod: {}'.format(self.hotswap_wotmod_path))
            print('[SkyRandomizer] Skybox packs directory: {}'.format(self.skybox_packs_path))
            print('[SkyRandomizer] ========================================')
            
            # Create directories if they don't exist
            if not os.path.exists(self.mods_path):
                os.makedirs(self.mods_path)
                print('[SkyRandomizer] Created mods directory')
            
            if not os.path.exists(self.skybox_packs_path):
                os.makedirs(self.skybox_packs_path)
                print('[SkyRandomizer] Created skyPacks directory')
            
            self._scan_available_packs()
            
            if self.available_packs:
                print('[SkyRandomizer] Installing initial skybox pack...')
                self._swap_skybox()
            else:
                print('[SkyRandomizer] ============================================')
                print('[SkyRandomizer] WARNING: No .wotmod files found!')
                print('[SkyRandomizer] Expected location: {}'.format(self.skybox_packs_path))
                print('[SkyRandomizer] Please place skybox .wotmod files there')
                print('[SkyRandomizer] Creating empty hotswap wotmod anyway...')
                print('[SkyRandomizer] ============================================')
                self._create_empty_hotswap_wotmod()
            
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
    
    def _force_delete_file(self, filepath):
        """Force delete a file even if it's locked by the game"""
        try:
            # First attempt: normal deletion
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print('[SkyRandomizer] Successfully deleted: {}'.format(filepath))
                    return True
                except Exception as e:
                    print('[SkyRandomizer] Normal delete failed (expected): {}'.format(e))
            
            # Second attempt: Move to temp then delete
            # Windows allows renaming locked files but not deleting them
            try:
                temp_name = filepath + '.old_{}'.format(random.randint(1000, 9999))
                if os.path.exists(filepath):
                    os.rename(filepath, temp_name)
                    print('[SkyRandomizer] Renamed locked file to: {}'.format(temp_name))
                    
                    # Try to delete the temp file (may fail if still locked)
                    try:
                        os.remove(temp_name)
                        print('[SkyRandomizer] Deleted temp file')
                    except:
                        print('[SkyRandomizer] Temp file still locked, will be cleaned up later')
                return True
            except Exception as e:
                print('[SkyRandomizer] Rename attempt failed: {}'.format(e))
            
            # If all else fails, we'll just overwrite it
            print('[SkyRandomizer] Will overwrite the file directly')
            return True
            
        except Exception as e:
            print('[SkyRandomizer] Force delete error: {}'.format(e))
            import traceback
            traceback.print_exc()
            return False
    
    def _cleanup_old_temp_files(self):
        """Clean up old .old_* temp files"""
        try:
            if not os.path.exists(self.mods_path):
                return
            
            for filename in os.listdir(self.mods_path):
                if '.old_' in filename and filename.startswith(self.hotswap_wotmod_name):
                    old_file = os.path.join(self.mods_path, filename)
                    try:
                        os.remove(old_file)
                        print('[SkyRandomizer] Cleaned up old temp file: {}'.format(filename))
                    except:
                        pass  # Still locked, skip
        except Exception as e:
            print('[SkyRandomizer] Cleanup warning: {}'.format(e))
    
    def _create_empty_hotswap_wotmod(self):
        """Create an empty hotswap wotmod file"""
        try:
            print('[SkyRandomizer] Creating empty hotswap wotmod...')
            
            # Create empty zip file (UNCOMPRESSED - ZIP_STORED)
            with zipfile.ZipFile(self.hotswap_wotmod_path, 'w', zipfile.ZIP_STORED) as zipf:
                # Add a meta.xml file to make it valid
                meta_content = '<?xml version="1.0" encoding="utf-8"?>\n<root>\n    <id>skyrandomizerHotSwap</id>\n    <version>1.0.0</version>\n    <n>Sky Randomizer HotSwap</n>\n    <description>Dynamically swapped skybox pack</description>\n</root>'
                zipf.writestr('meta.xml', meta_content, zipfile.ZIP_STORED)
            
            print('[SkyRandomizer] Empty hotswap wotmod created (uncompressed)')
            
        except Exception as e:
            print('[SkyRandomizer] Error creating empty wotmod: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _create_hotswap_wotmod_from_pack(self, source_wotmod_path):
        """Create/update the hotswap wotmod by copying content from source pack"""
        try:
            print('[SkyRandomizer] Creating hotswap wotmod from: {}'.format(source_wotmod_path))
            
            # Clean up old temp files first
            self._cleanup_old_temp_files()
            
            # Create in a temporary location first
            temp_fd, temp_wotmod = tempfile.mkstemp(suffix='.wotmod', dir=self.mods_path)
            os.close(temp_fd)
            
            try:
                # Copy content from source to temp file (UNCOMPRESSED)
                print('[SkyRandomizer] Extracting source pack to temporary wotmod (uncompressed)...')
                
                with zipfile.ZipFile(source_wotmod_path, 'r') as source_zip:
                    with zipfile.ZipFile(temp_wotmod, 'w', zipfile.ZIP_STORED) as target_zip:
                        file_count = 0
                        for item in source_zip.namelist():
                            data = source_zip.read(item)
                            # Write uncompressed
                            target_zip.writestr(item, data, zipfile.ZIP_STORED)
                            file_count += 1
                        
                        print('[SkyRandomizer] Copied {} files to temporary wotmod (uncompressed)'.format(file_count))
                
                # Now replace the hotswap file
                # Force delete/rename the old one if it exists
                self._force_delete_file(self.hotswap_wotmod_path)
                
                # Move temp file to final location
                # Use copy + delete instead of rename to bypass locks
                try:
                    shutil.copy2(temp_wotmod, self.hotswap_wotmod_path)
                    print('[SkyRandomizer] Hotswap wotmod created: {}'.format(self.hotswap_wotmod_path))
                    
                    # Try to delete temp file
                    try:
                        os.remove(temp_wotmod)
                    except:
                        print('[SkyRandomizer] Temp file cleanup will happen later')
                    
                    return True
                    
                except Exception as e:
                    print('[SkyRandomizer] Error moving temp file: {}'.format(e))
                    # If copy failed, try direct overwrite
                    try:
                        os.remove(self.hotswap_wotmod_path)
                    except:
                        pass
                    shutil.move(temp_wotmod, self.hotswap_wotmod_path)
                    print('[SkyRandomizer] Hotswap wotmod created (via move)')
                    return True
                
            except Exception as e:
                # Clean up temp file on error
                try:
                    os.remove(temp_wotmod)
                except:
                    pass
                raise e
                
        except Exception as e:
            print('[SkyRandomizer] Error creating hotswap wotmod: {}'.format(e))
            import traceback
            traceback.print_exc()
            return False
    
    def _swap_skybox(self):
        """Randomly select a pack and update the hotswap wotmod"""
        if not self.initialized or not self.mods_path:
            print('[SkyRandomizer] Not initialized yet, cannot swap')
            return
        
        if not self.available_packs:
            print('[SkyRandomizer] No skybox packs available to swap')
            return
        
        try:
            # Select a different pack than current
            selected_pack = random.choice(self.available_packs)
            
            if selected_pack == self.current_pack and len(self.available_packs) > 1:
                other_packs = [p for p in self.available_packs if p != self.current_pack]
                selected_pack = random.choice(other_packs)
            
            print('[SkyRandomizer] ===== SWAPPING SKYBOX =====')
            print('[SkyRandomizer] Selected: {}'.format(selected_pack))
            
            # Get source pack path
            source_wotmod_path = os.path.join(self.skybox_packs_path, selected_pack)
            
            # Create/update hotswap wotmod
            if self._create_hotswap_wotmod_from_pack(source_wotmod_path):
                # Aggressively purge ALL resource caches
                try:
                    print('[SkyRandomizer] Purging resource caches...')
                    ResMgr.purge('')  # Purge everything
                    print('[SkyRandomizer] Cache purged')
                except Exception as e:
                    print('[SkyRandomizer] Cache purge warning: {}'.format(e))
                
                self.current_pack = selected_pack
                
                print('[SkyRandomizer] ===== SWAP COMPLETE =====')
                print('[SkyRandomizer] Active pack: {}'.format(selected_pack))
                print('[SkyRandomizer] HotSwap wotmod updated: {}'.format(self.hotswap_wotmod_path))
                print('[SkyRandomizer] Changes should apply on next map load')
            else:
                print('[SkyRandomizer] ===== SWAP FAILED =====')
                print('[SkyRandomizer] Could not create hotswap wotmod')
            
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