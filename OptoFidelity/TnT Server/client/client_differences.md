# Client repository vs auto-generated differences

List of differences between TnT Client git repository (at commit c8f48c290) and auto-generated client.

tnt_audio_analyzer_client: OK

tnt_camera_client:
- can't support get_mjpeg_stream_url
    - can be removed and when updating to customer update their script
    - comment in start_continuous doctstring

tnt_dut_client
- lt, tr, bl, br now return dicts but TnT Client should return list (existing client converts dict to list)
    - server configuration has the corners as dicts so if we change to lists then config compatibility breaks
    - it is less likely that customers use the DUT client corners so lets change that to return dicts
- robot property: removed from client
  - this was used by get_robot_position(), press_physical_button() and move(), which will be implemented in server
    - if client has statement `dut.robot = robot` then I think this just creates attribute `robot` but should not be a problem
- path()
  - needed to add conversion from TnTDutPoint to dict (should not be visible to user)
- swipe(), drag(), drag_force(), tap() tilt and azimuth defaults from None to 0. Should not have effect because None was converted to 0 in server.
- multi_tap() implemented server side
- circle() added default value n=1 server side
- list_buttons() implemented server side
- press_physical_button() removed as there is no reason to have it in DUT client
    - implement if easy and mark deprecated -> remove
- screenshot() added default parameter camera_id="Camera1" server side
  - changed server to return name instead of {"name": name}
- search_text() added default parameter pattern=""
- show_image() image parameter is not automatically converted to base64 encoded bytes.
  - not compatible with tppt, what to do?
  - automatically convert bytes->base64
- filter_points(), filter_lines() changed parameter region_name in server to region for client compatibility

tnt_dut_positioning_client
- put_start_xyz_positioning(): added show_positioning_image parameter
- show_positioning_image(): added show_positioning_image parameter
- start_xyz_positioning(): added show_positioning_image parameter

tnt_hsup_client
- no inheritance
- some differences in docstrings

tnt_image_client: OK

tnt_microphone_client:
- put_record_audio(): changed parameter "duration" -> "record_duration" in server side for client compatibility
- removed property latest_recording in client and replaced by get_latest_recording (there was mapping from property to get_ method)
    - probably not used but need to fix if updated to customer

tnt_motherboard_client: OK

tnt_physical_button_client:
- expose properties jump_height, pressed_position, approach_position (not necessary but in cline with other clients)

tnt_robot_client:
- put_speed: override parameter (exists in server side) exposed in client but marked deprecated
- added put_move() for client move()
- put_change_tip(): removed parameter tool_name: not exposed in client nor used in TPPT
- change_tip() in client used to also accept TnTTipClient object as tip parameter. Now only name is accepted. Can break existing uses.
    - accept only string and fix customer scripts if necessary
- put_detach_tip(): removed parameter tool_name: not exposed in client nor used in TPPT
- get_position(): client used to remove keys "head" and "frame" from result dict. This is not done anymore.
    - add new parameter with default value to control the visibility of these keys

tnt_speaker_client: OK

tnt_surfaceprobe_client: OK

tnt_tip_client: OK