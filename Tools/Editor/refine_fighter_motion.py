"""Transfer mannequin leg articulation to the chapel rig and stagger the delivery of weapon poses."""
import math
import unreal as u

lib = u.EditorAssetLibrary
world, local = u.AnimPoseSpaces.WORLD, u.AnimPoseSpaces.LOCAL
options = u.AnimPoseEvaluationOptions()
folder = '/Game/SoulBreak/Animations/AN_'
source_folder = '/Game/Characters/Mannequins/Anims/Unarmed/'
version = 'HumanMotionV1'

def sample(clip, time):
    return clip.get_anim_pose_at_time(min(clip.get_play_length(), max(0, time)), options)

def save_tracks(clip, tracks, tag=version):
    ctl = clip.controller
    ctl.open_bracket('Refine fighter performance', False)
    try:
        for name, keys in tracks.items():
            assert ctl.set_bone_track_keys(name, [k.translation for k in keys],
                [k.rotation for k in keys], [k.scale3d for k in keys], False), name
    finally:
        ctl.close_bracket(False)
    lib.set_metadata_tag(clip, tag, '1')
    assert lib.save_loaded_asset(clip, False)

def gait(name, source):
    clip = lib.load_asset(folder+name)
    tag='RegisteredStrideV2'
    if lib.get_metadata_tag(clip, tag): return
    src = lib.load_asset(source_folder+source)
    ref, target = sample(src, 0), sample(clip, 0)
    # Register the rigs by their hip line; both use Z-up, but the pilgrim faces +Y.
    def hip_yaw(pose, left, right):
        v = pose.get_ref_bone_pose(left,world).translation - pose.get_ref_bone_pose(right,world).translation
        return math.atan2(v.y,v.x)
    yaw = hip_yaw(target,'ThighL','ThighR') - hip_yaw(ref,'thigh_l','thigh_r')
    align = u.Quat(0,0,math.sin(yaw/2),math.cos(yaw/2))
    joints = [(part+side, joint+'_'+side.lower()) for side in 'LR'
              for part,joint in [('Thigh','thigh'),('Shin','calf'),('Foot','foot')]]
    tracks = {dst:[] for dst,_ in joints}
    span = src.get_play_length()
    # Synchronise the imported heel strike with the existing upper-body gait cycle.
    forward = (0,1) if name in ('KnightWalk','Walk','Run') else (
        (0,-1) if name=='Backstep' else (-1,0) if name=='StrafeR' else (1,0))
    def lead(i):
        pos = sample(src,i*span/160)
        delta = align.rotate_vector(pos.get_bone_pose('foot_r',world).translation-pos.get_bone_pose('foot_l',world).translation)
        return delta.x*forward[0]+delta.y*forward[1]
    leads=[lead(i) for i in range(160)]
    peaks=[i for i in range(1,159) if leads[i]>=leads[i-1] and leads[i]>leads[i+1]
           and leads[i]>max(leads)*.6]
    assert len(peaks)>=2,(source,peaks)
    start,end=peaks[:2]
    frames = u.AnimationLibrary.get_num_frames(clip)+1
    for i in range(frames):
        t=i/(frames-1)
        srcpose=sample(src,(start+t*(end-start))*span/160)
        dstpose=sample(clip,t*clip.get_play_length())
        parent_rot=dstpose.get_bone_pose('Pelvis',world).rotation
        for dst, bone in joints:
            if dst.startswith('Thigh'): parent_rot=dstpose.get_bone_pose('Pelvis',world).rotation
            delta=srcpose.get_bone_pose(bone,world).rotation*ref.get_ref_bone_pose(bone,world).rotation.inversed()
            rot=align*delta*align.inversed()*target.get_ref_bone_pose(dst,world).rotation
            tr=dstpose.get_bone_pose(dst,local)
            tr.rotation=parent_rot.inversed()*rot
            tracks[dst].append(tr)
            parent_rot=rot
    # Close the measured cycle smoothly even when consecutive strides differ.
    for keys in tracks.values():
        correction=keys[-1].rotation.inversed()*keys[0].rotation
        for i,key in enumerate(keys):
            blend=max(0.,(i/(frames-1)-.75)*4)
            key.rotation=key.rotation*u.Quat(0,0,0,1).slerp_quat(correction,blend*blend*(3-2*blend))
    save_tracks(clip,tracks,tag)

def attack(name):
    clip=lib.load_asset(folder+name)
    if lib.get_metadata_tag(clip,version): return
    duration=clip.get_play_length()
    frames=u.AnimationLibrary.get_num_frames(clip)+1
    # Hips turn through the blow first. Hands retain the authored strike clock.
    offsets={'Pelvis':.046,'Chest':.019,'Head':.025,'CloakTop':-.018,'CloakMid':-.042,'CloakHem':-.068}
    tracks={joint:[] for joint in offsets}
    for i in range(frames):
        t=i/(frames-1)
        for joint,offset in offsets.items():
            at=t*duration+offset*math.sin(math.pi*t)**2
            tracks[joint].append(sample(clip,at).get_bone_pose(joint,local))
    save_tracks(clip,tracks)

for dst,src in [('KnightWalk','Walk/MF_Unarmed_Walk_Fwd'),('Walk','Jog/MF_Unarmed_Jog_Fwd'),
                ('Run','Jog/MF_Unarmed_Jog_Fwd'),('Backstep','Walk/MF_Unarmed_Walk_Bwd'),
                ('StrafeR','Walk/MF_Unarmed_Walk_Right'),('StrafeL','Walk/MF_Unarmed_Walk_Left')]:
    gait(dst,src)
for dst in ['Cut','ReturnCut','LowCut','LowReturnCut','OathCut','LowOathCut','SwordSweep','Bash','ShoulderCheck']:
    attack(dst)
u.log('FIGHTER_MOTION_BAKED')

