"""
SkyRandomizer - Preload Strategy Skybox Randomizer for World of Tanks

AUTOMATIC COMBINED WOTMOD BUILDING:
This mod automatically combines all skybox .wotmod files from ./mods/skyPacks/
into a single skyRandomizer_AllPacks.wotmod file on game startup.

SMART REBUILD LOGIC:
- First run: Builds combined pack automatically
- Subsequent runs: Only rebuilds if:
  * Source packs were added/removed
  * Source packs are newer than combined pack
  * Number of packs changed
- If already up-to-date: Skips rebuild for faster startup

HOW IT WORKS:
1. Startup: Combines all packs into one .wotmod (each as spaces/sky_pack_XX/)
2. Runtime: Switches which skybox path is used (no file operations)
3. Battle-to-battle: Picks random pack after each battle

INSTALLATION:
1. Place skybox .wotmod files in: ./mods/skyPacks/
2. Place this file in: ./mods/1.XX.X.X/
3. Launch game - combined pack builds automatically

CRITICAL: The _hook_space_loading() method needs WoT-specific API implementation
to redirect skybox paths at runtime. See IMPLEMENTATION_GUIDE.md for details.
"""

import os
import random
import zipfile
import BigWorld
import ResMgr

print('[SkyRandomizer] ===== MOD LOADING =====')

try:
    from PlayerEvents import g_playerEvents
    print('[SkyRandomizer] PlayerEvents imported successfully')
except Exception as e:
    print('[SkyRandomizer] ERROR importing PlayerEvents: {}'.format(e))

try:
    from Avatar import PlayerAvatar
    print('[SkyRandomizer] Avatar imported successfully')
except Exception as e:
    print('[SkyRandomizer] ERROR importing Avatar: {}'.format(e))

class SkyboxRandomizer:
    def __init__(self):
        print('[SkyRandomizer] Initializing SkyboxRandomizer...')
        try:
            self.skybox_packs_path = './mods/skyPacks/'
            self.combined_wotmod_name = 'skyRandomizer_AllPacks.wotmod'
            self.mods_path = None  # Will be set to ./mods/{version}/
            self.available_packs = []  # List of pack folder names inside the wotmod
            self.current_pack = None
            self.initialized = False
            self.space_loading_hooked = False
            
            print('[SkyRandomizer] Source packs path: {}'.format(self.skybox_packs_path))
            print('[SkyRandomizer] Strategy: Preload all packs, switch paths at runtime')
            
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
            print('[SkyRandomizer] Mods directory: {}'.format(self.mods_path))
            print('[SkyRandomizer] Combined wotmod: {}'.format(self.combined_wotmod_name))
            print('[SkyRandomizer] Skybox packs directory: {}'.format(self.skybox_packs_path))
            print('[SkyRandomizer] ========================================')
            
            # Create directories if they don't exist
            if not os.path.exists(self.mods_path):
                os.makedirs(self.mods_path)
                print('[SkyRandomizer] Created mods directory')
            
            if not os.path.exists(self.skybox_packs_path):
                os.makedirs(self.skybox_packs_path)
                print('[SkyRandomizer] Created skyPacks directory')
            
            # Check if combined wotmod needs to be built/rebuilt
            combined_wotmod_path = os.path.join(self.mods_path, self.combined_wotmod_name)
            should_rebuild = False
            
            if not os.path.exists(combined_wotmod_path):
                print('[SkyRandomizer] Combined wotmod not found')
                should_rebuild = True
            else:
                # Check if source packs are newer than combined wotmod
                if self._source_packs_changed(combined_wotmod_path):
                    print('[SkyRandomizer] Source packs have changed since last build')
                    should_rebuild = True
                else:
                    print('[SkyRandomizer] Combined wotmod is up to date: {}'.format(self.combined_wotmod_name))
            
            if should_rebuild:
                print('[SkyRandomizer] Building combined wotmod from source packs...')
                if self._create_combined_wotmod():
                    print('[SkyRandomizer] ===== COMBINED WOTMOD CREATED =====')
                    print('[SkyRandomizer] Location: {}'.format(combined_wotmod_path))
                    print('[SkyRandomizer] ===================================')
                    # Scan what packs are available inside the combined wotmod
                    self._scan_available_packs_in_wotmod(combined_wotmod_path)
                else:
                    print('[SkyRandomizer] WARNING: Failed to create combined wotmod')
                    print('[SkyRandomizer] Please add skybox .wotmod files to: {}'.format(self.skybox_packs_path))
                    # Still try to scan existing wotmod if build failed
                    if os.path.exists(combined_wotmod_path):
                        print('[SkyRandomizer] Attempting to use existing combined wotmod...')
                        self._scan_available_packs_in_wotmod(combined_wotmod_path)
            else:
                # Use existing combined wotmod
                self._scan_available_packs_in_wotmod(combined_wotmod_path)
            
            if self.available_packs:
                # Pick initial random skybox
                self.current_pack = random.choice(self.available_packs)
                print('[SkyRandomizer] Initial skybox pack: {}'.format(self.current_pack))
            else:
                print('[SkyRandomizer] ============================================')
                print('[SkyRandomizer] WARNING: No skybox packs found!')
                print('[SkyRandomizer] Please place skybox .wotmod files in: {}'.format(self.skybox_packs_path))
                print('[SkyRandomizer] Then restart the game to generate the combined pack')
                print('[SkyRandomizer] ============================================')
            
            self.initialized = True
            print('[SkyRandomizer] Initialization complete!')
            
        except Exception as e:
            print('[SkyRandomizer] ERROR during delayed initialization: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    
    def _source_packs_changed(self, combined_wotmod_path):
        """Check if source packs have been added/changed since combined wotmod was built"""
        try:
            if not os.path.exists(self.skybox_packs_path):
                return False
            
            # Get modification time of combined wotmod
            combined_mtime = os.path.getmtime(combined_wotmod_path)
            
            # Check all source .wotmod files
            source_wotmods = [f for f in os.listdir(self.skybox_packs_path) if f.endswith('.wotmod')]
            
            # If no source files, no need to rebuild
            if not source_wotmods:
                return False
            
            # Check if any source file is newer than combined wotmod
            for source_wotmod in source_wotmods:
                source_path = os.path.join(self.skybox_packs_path, source_wotmod)
                if os.path.getmtime(source_path) > combined_mtime:
                    print('[SkyRandomizer] Source pack is newer: {}'.format(source_wotmod))
                    return True
            
            # Check if number of packs changed by comparing with what's inside combined wotmod
            try:
                with zipfile.ZipFile(combined_wotmod_path, 'r') as z:
                    all_paths = z.namelist()
                    pack_folders = set()
                    for path in all_paths:
                        if path.startswith('spaces/'):
                            parts = path.split('/')
                            if len(parts) >= 2:
                                pack_folders.add(parts[1])
                    
                    if len(pack_folders) != len(source_wotmods):
                        print('[SkyRandomizer] Number of packs changed: {} source files, {} packs in combined'.format(
                            len(source_wotmods), len(pack_folders)
                        ))
                        return True
            except Exception as e:
                print('[SkyRandomizer] Could not check combined wotmod contents: {}'.format(e))
                # If we can't read it, safer to rebuild
                return True
            
            return False
            
        except Exception as e:
            print('[SkyRandomizer] Error checking source packs: {}'.format(e))
            # On error, rebuild to be safe
            return True
    
    def _create_combined_wotmod(self):
        """Create a single combined wotmod containing all skybox packs"""
        try:
            print('[SkyRandomizer] ===== CREATING COMBINED WOTMOD =====')
            
            # Scan for source .wotmod files
            if not os.path.exists(self.skybox_packs_path):
                print('[SkyRandomizer] No skyPacks directory found')
                return False
            
            source_wotmods = [f for f in os.listdir(self.skybox_packs_path) if f.endswith('.wotmod')]
            
            if not source_wotmods:
                print('[SkyRandomizer] No .wotmod files found in {}'.format(self.skybox_packs_path))
                return False
            
            print('[SkyRandomizer] Found {} source packs:'.format(len(source_wotmods)))
            for pack in source_wotmods:
                print('[SkyRandomizer]   - {}'.format(pack))
            
            combined_path = os.path.join(self.mods_path, self.combined_wotmod_name)
            
            # Delete existing combined wotmod if it exists (rebuild every time)
            if os.path.exists(combined_path):
                try:
                    print('[SkyRandomizer] Removing old combined wotmod...')
                    os.remove(combined_path)
                except Exception as e:
                    print('[SkyRandomizer] WARNING: Could not delete old combined wotmod: {}'.format(e))
                    print('[SkyRandomizer] This may cause issues if source packs have changed')
            
            print('[SkyRandomizer] Building new combined wotmod...')
            total_files = 0
            
            with zipfile.ZipFile(combined_path, 'w', zipfile.ZIP_STORED) as combined_zip:
                for idx, source_wotmod in enumerate(source_wotmods):
                    pack_name = 'sky_pack_{:02d}'.format(idx)
                    source_path = os.path.join(self.skybox_packs_path, source_wotmod)
                    
                    print('[SkyRandomizer] Pack {}/{}: {} -> {}'.format(
                        idx + 1, len(source_wotmods), source_wotmod, pack_name
                    ))
                    
                    pack_files = 0
                    with zipfile.ZipFile(source_path, 'r') as source_zip:
                        for item in source_zip.namelist():
                            # Rewrite path to be under spaces/{pack_name}/
                            new_path = 'spaces/{}/{}'.format(pack_name, item)
                            data = source_zip.read(item)
                            combined_zip.writestr(new_path, data, zipfile.ZIP_STORED)
                            pack_files += 1
                            total_files += 1
                    
                    print('[SkyRandomizer]   Added {} files'.format(pack_files))
            
            print('[SkyRandomizer] ===== COMBINED WOTMOD CREATED =====')
            print('[SkyRandomizer] Location: {}'.format(combined_path))
            print('[SkyRandomizer] Total packs: {}'.format(len(source_wotmods)))
            print('[SkyRandomizer] Total files: {}'.format(total_files))
            print('[SkyRandomizer] ====================================')
            return True
            
        except Exception as e:
            print('[SkyRandomizer] Error creating combined wotmod: {}'.format(e))
            import traceback
            traceback.print_exc()
            return False
    
    def _scan_available_packs_in_wotmod(self, wotmod_path):
        """Scan the combined wotmod to find available pack folders"""
        try:
            if not os.path.exists(wotmod_path):
                print('[SkyRandomizer] Combined wotmod not found: {}'.format(wotmod_path))
                return
            
            print('[SkyRandomizer] Scanning combined wotmod for packs...')
            
            with zipfile.ZipFile(wotmod_path, 'r') as z:
                all_paths = z.namelist()
                
                # Find unique pack folders under spaces/
                pack_folders = set()
                for path in all_paths:
                    if path.startswith('spaces/'):
                        parts = path.split('/')
                        if len(parts) >= 2:
                            pack_folders.add(parts[1])
                
                self.available_packs = sorted(list(pack_folders))
                
                if self.available_packs:
                    print('[SkyRandomizer] Found {} packs in combined wotmod:'.format(len(self.available_packs)))
                    for pack in self.available_packs:
                        print('[SkyRandomizer]   - {}'.format(pack))
                else:
                    print('[SkyRandomizer] No packs found in combined wotmod')
                    
        except Exception as e:
            print('[SkyRandomizer] Error scanning combined wotmod: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _register_events(self):
        """Register game events"""
        try:
            g_playerEvents.onAccountBecomePlayer += self._on_account_ready
            print('[SkyRandomizer] Events registered successfully')
        except Exception as e:
            print('[SkyRandomizer] ERROR registering events: {}'.format(e))
    
    def _hook_avatar_destruction(self):
        """Hook into Avatar destruction to swap after battle ends"""
        try:
            original_onLeaveWorld = PlayerAvatar.onLeaveWorld
            
            def hooked_onLeaveWorld(self):
                print('[SkyRandomizer] Avatar leaving world - battle ended!')
                g_skyboxRandomizer._on_battle_ended()
                return original_onLeaveWorld(self)
            
            PlayerAvatar.onLeaveWorld = hooked_onLeaveWorld
            print('[SkyRandomizer] Avatar destruction hook installed')
        except Exception as e:
            print('[SkyRandomizer] ERROR hooking avatar destruction: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _hook_space_loading(self):
        """Hook into space/map loading to inject our custom skybox path"""
        if self.space_loading_hooked:
            return
        
        try:
            # This is where you'd hook BigWorld.loadSpace or similar
            # The exact API depends on WoT's Python API version
            # Common approaches:
            
            # Option 1: Hook BigWorld.loadResourceListBG
            # Option 2: Hook space XML loading
            # Option 3: Override space descriptor paths
            
            # Placeholder - needs actual WoT API knowledge
            print('[SkyRandomizer] Space loading hook: This needs WoT-specific API')
            print('[SkyRandomizer] You need to hook the function that loads space descriptors')
            print('[SkyRandomizer] And modify the skybox/cubemap path to point to: spaces/{}/'.format(self.current_pack))
            
            # Example pseudocode:
            # original_loadSpace = BigWorld.loadSpace
            # def hooked_loadSpace(spacePath, *args, **kwargs):
            #     # Modify spacePath or descriptor to use our custom sky
            #     return original_loadSpace(spacePath, *args, **kwargs)
            # BigWorld.loadSpace = hooked_loadSpace
            
            self.space_loading_hooked = True
            
        except Exception as e:
            print('[SkyRandomizer] ERROR hooking space loading: {}'.format(e))
            import traceback
            traceback.print_exc()
    
    def _on_battle_ended(self):
        """Called when battle ends - pick new skybox for next battle"""
        if not self.initialized or not self.available_packs:
            return
        
        print('[SkyRandomizer] ===== BATTLE ENDED - SELECTING NEW SKYBOX =====')
        
        # Pick a different pack than current
        if len(self.available_packs) > 1:
            other_packs = [p for p in self.available_packs if p != self.current_pack]
            self.current_pack = random.choice(other_packs)
        else:
            self.current_pack = self.available_packs[0]
        
        print('[SkyRandomizer] Next battle will use: {}'.format(self.current_pack))
        print('[SkyRandomizer] Path: spaces/{}/'.format(self.current_pack))
    
    def _on_account_ready(self):
        """Called when account becomes player (garage loaded)"""
        if not self.initialized:
            print('[SkyRandomizer] Account ready, completing initialization...')
            self._complete_initialization()
            # Install hooks
            self._hook_avatar_destruction()
            self._hook_space_loading()
        else:
            print('[SkyRandomizer] Returned to garage')

print('[SkyRandomizer] Creating mod instance...')
try:
    g_skyboxRandomizer = SkyboxRandomizer()
    print('[SkyRandomizer] ===== MOD LOADED SUCCESSFULLY =====')
except Exception as e:
    print('[SkyRandomizer] ===== FATAL ERROR =====')
    print('[SkyRandomizer] Failed to initialize: {}'.format(e))
    import traceback
    traceback.print_exc()