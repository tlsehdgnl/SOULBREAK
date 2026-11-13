"""Pose the shared FK skeleton, then solve feet and sword-arm endpoints in model space."""
from math import sin,cos,pi,sqrt,radians
import bpy
from mathutils import Euler, Matrix, Vector


GUARD = dict(Chest=(-3,2,-8), Pelvis=(3,0,4), Head=(2,-2,5), UpperArmR=(-10,-12,-8),
             ForearmR=(-32,0,4),UpperArmL=(-15,11,12),ForearmL=(-36,-1,-8),
             ThighR=(-9,1,-2),ShinR=(14,0,0),ThighL=(8,0,2),ShinL=(7,0,0),
             hip=(0,0,-2),sword=((-36,-21,93),(-.44,-.75,.49)))


class Performance:
    def __init__(self, arm, rig, scene, export):
        self.arm=arm
        self.rig=rig
        self.scene=scene
        self.export=export
        self.pose=rig.pose.bones
        self.previous={}
        self.scene.render.fps=60

    def point_bone(self, bone, original, direction):
        original=Vector(original)
        direction=Vector(direction)
        if original.length<.001 or direction.length<.001:
            return
        rotation=original.normalized().rotation_difference(direction.normalized())
        center=bone.head.copy()
        bone.matrix=(Matrix.Translation(center)@rotation.to_matrix().to_4x4()@
                     Matrix.Translation(-center)@bone.matrix)
        bone.scale=(1,1,1)
        bpy.context.view_layer.update()

    def two_bone(self, upper, lower, end, target, pole):
        """Solve a rigid two-link chain with an anatomical bend plane, without stretching."""
        upper=self.pose[upper]
        lower=self.pose[lower]
        tip=self.pose[end]
        start=upper.head.copy()
        a=(lower.head-start).length
        b=(tip.head-lower.head).length
        direction=Vector(target)-start
        distance=min(a+b-.02,max(abs(a-b)+.02,direction.length))
        direction.normalize()
        bend=Vector(pole)-start
        bend=(bend-direction*bend.dot(direction)).normalized()
        along=(a*a-b*b+distance*distance)/(2*distance)
        elbow=start+direction*along+bend*sqrt(max(0,a*a-along*along))
        self.point_bone(upper,lower.head-start,elbow-start)
        self.point_bone(lower,tip.head-lower.head,start+direction*distance-lower.head)

    def key(self, frame, settings):
        self.scene.frame_set(frame)
        spec={**GUARD,**settings}
        for b in self.pose:
            b.rotation_mode='QUATERNION'
            b.scale=(1,1,1)
            basis=self.arm.bones[b.name].matrix_local.to_quaternion()
            angles=spec.get(b.name,(0,0,0))
            rot=Euler(tuple(radians(v) for v in angles)).to_quaternion()
            b.rotation_quaternion=basis.inverted()@rot@basis
            b.location=basis.inverted()@Vector(spec['hip']) if b.name=='Pelvis' else Vector()
        bpy.context.view_layer.update()
        for side,foot in spec.get('feet',{}).items():
            point,pitch=foot
            s=-1 if side=='R' else 1
            self.two_bone('Thigh'+side,'Shin'+side,'Foot'+side,point,(s*13,-85,54))
            b=self.pose['Foot'+side]
            self.point_bone(b,b.tail-b.head,(0,-cos(radians(pitch)),sin(radians(pitch))))
        swing=spec['sword']
        if swing:
            grip,line=swing
            self.two_bone('UpperArmR','ForearmR','HandR',grip,(-82,8,120))
            self.point_bone(self.pose['HandR'],self.pose['BladeTip'].head-self.pose['BladeBase'].head,line)
        # Keep a strapped heater braced toward the opponent while the elbow flexes.
        # The plate joint is also the independent gameplay detach point.
        shield=self.pose['ShieldPlate']
        shield_angles=settings.get('shield',(4,-8,-15))
        if shield_angles is not None:
            facing=Euler(tuple(radians(x) for x in shield_angles)).to_matrix().to_4x4()
            rest=self.arm.bones['ShieldPlate'].matrix_local.to_quaternion().to_matrix().to_4x4()
            shield.matrix=Matrix.Translation(shield.head)@facing@rest
            shield.scale=(1,1,1)
            bpy.context.view_layer.update()
        # A rigid blade must retain its bind-pose length in every authored beat.
        # Nonunit scale left by an IK matrix decomposition used to compound over clips.
        tip=self.pose['BladeTip'].head-self.pose['BladeBase'].head
        bind=self.arm.bones['BladeTip'].head_local-self.arm.bones['BladeBase'].head_local
        if abs(tip.length-bind.length)>.1:
            raise ValueError(f'Sword deformed at frame {frame}: {tip.length:.3f} cm')
        for b in self.pose:
            q=b.rotation_quaternion.copy()
            if b.name in self.previous:
                q.make_compatible(self.previous[b.name])
            b.rotation_quaternion=q
            self.previous[b.name]=q
            b.keyframe_insert(data_path='rotation_quaternion',frame=frame)
            if b.name=='Pelvis':
                b.keyframe_insert(data_path='location',frame=frame)

    def clip(self, name, duration, beats):
        action=bpy.data.actions.new(name)
        self.rig.animation_data_create()
        self.rig.animation_data.action=action
        self.previous={}
        frames=round(duration*60)
        self.scene.frame_start=1
        self.scene.frame_end=1+frames
        for i,(fraction,pose) in enumerate(beats):
            previous=beats[max(0,i-1)][1]
            chest=pose.get('Chest',GUARD['Chest'])
            prev=previous.get('Chest',GUARD['Chest'])
            gait=name in ('Idle','KnightIdle','Walk','Run','KnightWalk','StrafeR','StrafeL','Backstep')
            wave=sin(2*pi*fraction)
            # Inertia concentrates at the bias-cut hem. The top follows the shoulder
            # and settles first; the lower two joints carry the delayed twist.
            fullness=(4.0 if gait else 2.5)+max(0,pose.get('hip',(0,0,0))[1]*-.4)
            lag_yaw=(prev[2]-chest[2])*.22
            drift=wave*(2 if 'Idle' in name else 4) if gait else lag_yaw
            authored={'CloakTop':(fullness*.35,drift*.19,-chest[2]*.12),
                      'CloakMid':(fullness*.55,drift*.36,-chest[2]*.2+lag_yaw*.46),
                      'CloakHem':(fullness*.73,drift*.58,-chest[2]*.2+lag_yaw*.58),**pose}
            self.key(1+round(fraction*frames),authored)
        if hasattr(action,'fcurves'):
            curves=action.fcurves
        else:
            slot=self.rig.animation_data.action_slot
            curves=action.layers[0].strips[0].channelbag(slot).fcurves
        for curve in curves:
            for key in curve.keyframe_points:
                key.handle_left_type='AUTO_CLAMPED'
                key.handle_right_type='AUTO_CLAMPED'
        self.scene.frame_set(1)
        self.export('AN_'+name,[self.rig],True)

    @staticmethod
    def stride(phase, travel, run=False):
        targets={}
        for side,offset in [('R',0),('L',.5)]:
            s=-1 if side=='R' else 1
            t=(phase+offset)%1
            # Contact and driven push-off occupy 55%; the returning heel lifts, passes,
            # then extends for the next contact. The ankle stays level during support.
            if t<.55:
                p=t/.55
                sweep=1-2*p
                lift=0
                pitch=7*(1-min(1,p*3))-18*max(0,(p-.65)/.35)
            else:
                p=(t-.55)/.45
                sweep=-cos(pi*p)
                lift=(30 if run else 17)*sin(pi*p)**1.35
                pitch=-22*sin(pi*p)+8*p
            dx=travel[0]*sweep
            dy=travel[1]*sweep
            targets[side]=((s*14+dx,dy,10+lift),pitch)
        c=cos(2*pi*phase);q=sin(2*pi*phase)
        down=.5+.5*cos(4*pi*(phase-.12))
        return dict(feet=targets,hip=(2.3*c,-3 if run else -1,-7-down*(4 if run else 2.5)),
                    Pelvis=(2,-3.1*c,-5.2*c),Chest=(6 if run else 2,3*c,7*c),Head=(-2,-1.8*c,-3*c),
                    UpperArmL=(-17+(36 if run else 26)*c,9,-10*c),ForearmL=(-36-18*c,0,-4),
                    sword=((-34+2*q,-19-5*c,98+4*q),(-.40,-.74+.12*c,.37-.14*c)))

    def author_all(self):
        inhale=dict(Chest=(-5,1,-10),hip=(.5,0,-1),Head=(1,-2,7),ForearmL=(-40,-1,-7),
                    sword=((-35,-22,95),(-.42,-.69,.55)))
        self.clip('Idle',2.8,[(0,{}),(.45,inhale),(.68,{**inhale,'Head':(-1,0,3)}),(1,{})])
        braced=dict(hip=(1,0,-5),Chest=(-3,-4,-13),Head=(1,2,11),UpperArmL=(-36,12,3),
                    ForearmL=(-48,-3,8),sword=((-40,-16,94),(-.65,-.68,.29)))
        self.clip('KnightIdle',3.25,[(0,braced),(.42,{**braced,'hip':(1,0,-3),'Chest':(-5,-5,-15),
                  'sword':((-40,-17,97),(-.62,-.65,.34))}),(1,braced)])
        for name,travel,duration in [('Walk',(0,-29),.74),('Run',(0,-41),.59),
                ('StrafeR',(-18,-3),.65),('StrafeL',(18,-3),.65),('Backstep',(0,20),.69)]:
            self.clip(name,duration,[(i/12,self.stride(i/12,travel,name=='Run')) for i in range(13)])

        stance={'R':((-15,11,10),-4),'L':((15,-12,10),0)}
        wind=dict(hip=(-4,4,-10),Pelvis=(-1,-5,-21),Chest=(-8,-6,-29),Head=(2,7,43),feet=stance,
                  UpperArmL=(-13,16,21),sword=((-47,3,144),(-.78,.51,.34)))
        strike=dict(hip=(-2,-5,-9),Pelvis=(4,0,-5),Chest=(8,-2,-4),Head=(-3,3,5),feet=stance,
                    UpperArmL=(4,12,-8),sword=((-38,-38,133),(-.49,-.85,.15)))
        cross=dict(hip=(4,-8,-9),Pelvis=(5,4,18),Chest=(13,4,28),Head=(-6,-3,-28),feet=stance,
                   UpperArmL=(12,19,-10),sword=((-4,-40,117),(.67,-.72,-.19)))
        follow=dict(hip=(4,-4,-6),Pelvis=(4,3,22),Chest=(10,4,33),Head=(-3,-2,-36),feet=stance,
                    sword=((4,-22,109),(.89,.24,-.35)))
        self.clip('Cut',.60,[(0,{}),(.17,wind),(.28,wind),(.39,strike),(.52,cross),(.64,follow),(.83,follow),(1,{})])
        reverse_wind={**follow,'hip':(4,2,-10),'sword':((3,-18,108),(.91,.26,-.21))}
        reverse_hit={**strike,'Chest':(8,1,6),'sword':((-17,-38,134),(.27,-.94,.22))}
        reverse_end={**wind,'hip':(-4,-3,-7),'sword':((-48,-12,152),(-.84,.10,.48))}
        self.clip('ReturnCut',.75,[(0,follow),(.19,reverse_wind),(.28,reverse_wind),
                  (.41,reverse_hit),(.53,reverse_end),(.69,reverse_end),(1,{})])
        raised={**wind,'hip':(-5,4,-7),'sword':((-34,-6,166),(-.34,.17,.93)),
                'UpperArmL':(-38,11,12),'ForearmL':(-51,0,5)}
        self.clip('SwordSweep',1.60,[(0,braced),(.20,wind),(.34,raised),(.405,raised),
                  (.454,strike),(.50,cross),(.62,follow),(.79,follow),(1,braced)])
        parry=dict(hip=(-2,-1,-7),Pelvis=(2,1,12),Chest=(0,3,17),Head=(2,-4,-20),feet=stance,
                   UpperArmL=(-49,12,10),ForearmL=(-58,0,23),sword=((-24,-36,129),(.60,-.15,.79)))
        recoil={**parry,'hip':(-4,3,-10),'Chest':(-8,-3,10),'sword':((-28,-26,128),(.71,.08,.69))}
        self.clip('Parry',.5,[(0,{}),(.09,parry),(.26,parry),(.42,recoil),(.65,parry),(1,{})])
        draw={**wind,'hip':(-5,4,-16),'Chest':(18,-8,-32),'sword':((-39,1,84),(-.73,.64,-.21))}
        rise={**follow,'hip':(3,-10,-7),'Chest':(-9,7,38),'sword':((3,-26,165),(.47,.20,.86))}
        self.clip('OathCut',.85,[(0,{}),(.21,draw),(.32,draw),(.45,{**strike,'sword':((-30,-41,111),(-.25,-.95,.16))}),
                  (.57,rise),(.70,rise),(.85,{**rise,'hip':(3,-3,-4)}),(1,{})])

        brace={**braced,'hip':(-3,4,-11),'Chest':(-11,-3,15),'UpperArmL':(-46,13,-9),'ForearmL':(-54,0,16),'feet':stance}
        shove={**braced,'hip':(6,-10,-10),'Chest':(18,5,-28),'UpperArmL':(-82,-12,11),
               'ForearmL':(-11,0,4),'sword':((-42,6,91),(-.83,.43,.14)),'feet':stance}
        self.clip('Bash',1.27,[(0,braced),(.23,brace),(.35,brace),(.45,shove),(.56,shove),(.78,braced),(1,braced)])
        lift={**braced,'hip':(-8,2,2),'Pelvis':(-7,-8,-5),'Chest':(-11,-5,6),'Head':(4,4,-5),
              'UpperArmL':(-25,25,10),'ThighL':(-80,-5,0),'ShinL':(97,0,0),'FootL':(0,0,0),
              'sword':((-46,-3,126),(-.78,-.13,.62))}
        crash={**braced,'hip':(5,-4,-18),'Chest':(24,11,-14),'Head':(-10,-7,13),
               'feet':{'R':((-14,7,10),-4),'L':((18,-18,10),2)},'UpperArmL':(-31,10,0)}
        self.clip('Stomp',2.05,[(0,braced),(.13,{**brace,'hip':(-5,4,-11)}),(.29,lift),(.42,lift),
                  (.46,crash),(.51,{**crash,'hip':(4,-5,-21)}),(.64,crash),(.87,braced),(1,braced)])
        tuck=dict(Chest=(33,7,5),Head=(29,-5,-5),ThighR=(-83,0,0),ThighL=(-57,5,3),ShinR=(113,0,0),ShinL=(89,0,0),
                  UpperArmR=(-49,-13,-8),ForearmR=(-57,0,10),UpperArmL=(-69,6,0),ForearmL=(-67,3,-5),sword=None)
        self.clip('Evade',.48,[(0,{}),(.18,{**tuck,'Pelvis':(36,-7,-7),'hip':(-3,-4,-27)}),
                  (.38,{**tuck,'Pelvis':(126,-10,-10),'hip':(-5,-5,-20)}),
                  (.62,{**tuck,'Pelvis':(224,-12,-8),'hip':(-5,-5,-18)}),
                  (.83,{**tuck,'Pelvis':(321,-6,-4),'hip':(-2,-3,-27)}),(1,{'Pelvis':(360,0,0)})])
        flinch=dict(hip=(-5,7,-12),Chest=(-23,-14,-24),Pelvis=(-7,4,8),Head=(-17,7,-13),
                    UpperArmL=(6,44,13),feet=stance,sword=((-50,2,115),(-.81,.25,.48)))
        self.clip('Stagger',1,[(0,{}),(.12,flinch),(.23,{**flinch,'Head':(-21,6,-16)}),
                  (.44,{**flinch,'Chest':(-8,-8,-15),'hip':(-6,9,-15)}),(.68,braced),(1,{})])
        fall=dict(Chest=(20,-13,-10),Head=(18,0,-9),UpperArmL=(-21,46,0),UpperArmR=(-32,-35,0),
                  ForearmR=(-13,0,5),ThighL=(-44,0,0),ShinL=(52,0,0),sword=None)
        self.clip('Death',1.25,[(0,{}),(.21,flinch),(.46,{**fall,'Pelvis':(-19,33,-8),'hip':(0,0,-39)}),
                  (.79,{**fall,'Pelvis':(-27,86,-10),'hip':(0,0,-70)}),
                  (1,{**fall,'Pelvis':(-24,83,-8),'hip':(0,0,-72)})])
        hit={**flinch,'hip':(-3,4,-8),'Chest':(-17,-8,-18),'Head':(-11,6,-9),
             'sword':((-42,-8,106),(-.68,-.29,.64))}
        self.clip('HitReact',.40,[(0,{}),(.14,hit),(.31,{**hit,'hip':(-4,5,-10),'Chest':(-24,-12,-21)}),
                   (.65,{**hit,'Chest':(-8,-5,-12),'hip':(-2,2,-6)}),(1,{})])
        wound=dict(hip=(6,5,-13),Pelvis=(1,12,8),Chest=(-19,17,25),Head=(20,-17,28),
                   UpperArmL=(-65,-21,32),ForearmL=(-80,4,45),feet=stance,sword=None)
        knee={**wound,'hip':(4,1,-31),'Chest':(25,18,20),'Head':(21,-12,20),'UpperArmL':(-43,-19,32)}
        rally={**braced,'hip':(2,2,-11),'Chest':(-4,8,-7),'Head':(7,-9,1),'UpperArmL':(-41,9,11)}
        self.clip('Sunder',1.0,[(0,braced),(.11,wound),(.29,knee),(.51,knee),(.72,rally),(1,braced)])


        # The heel set and overstepping weight transfer are heavier than the pilgrim's.
        def guard_step(t):
            step=self.stride(t,(0,-22))
            step['hip']=(2.9*cos(2*pi*t),-1.2,-6.8-3.2*cos(2*pi*(t-.1))**2)
            step.update(UpperArmL=(-40+6*cos(2*pi*t),10,7),ForearmL=(-53,0,12),
                        Chest=(4,3*cos(2*pi*t),-13+4.3*cos(2*pi*t)),
                        sword=((-38,-18,105+2*sin(2*pi*t)),(-.44,-.79,.28)))
            return step
        self.clip('KnightWalk',.98,[(i/12,guard_step(i/12)) for i in range(13)])
        crouch={**brace,'hip':(-4,7,-18),'Pelvis':(4,-5,10),'Chest':(17,-9,-24),
                'Head':(-13,9,16),'UpperArmL':(-62,5,14),'ForearmL':(-55,-4,9),
                'shield':(-13,3,6),'sword':((-44,2,96),(-.66,.72,.17))}
        push={**crouch,'hip':(2,-10,-13),'Pelvis':(5,4,13),'Chest':(20,-4,-28),
              'UpperArmL':(-65,-6,14),'ForearmL':(-28,0,7),
              'feet':{'L':((16,-24,10),4),'R':((-15,23,15),-23)},'shield':(-7,4,5)}
        drive={**push,'hip':(-3,-8,-14),'feet':{'R':((-16,-18,10),1),'L':((15,16,18),-18)}}
        arrest={**push,'hip':(2,-6,-22),'Chest':(26,8,-8),'Head':(-14,-4,8),
                'shield':(-18,-8,-12),'feet':{'R':((-17,21,10),-7),'L':((15,-24,10),2)}}
        self.clip('ShieldCharge',2.39,[(0,braced),(.14,crouch),(.308,crouch),(.365,push),
                  (.42,drive),(.485,push),(.519,arrest),(.62,arrest),(.79,brace),(1,braced)])
        curl=dict(hip=(-3,2,-17),Pelvis=(7,-7,-8),Chest=(31,9,-13),Head=(17,5,7),
                  UpperArmR=(-30,-13,18),ForearmR=(-71,8,-13),UpperArmL=(-32,8,-17),ForearmL=(-75,3,15),
                  sword=None,feet=stance)
        roar={**curl,'hip':(1,-3,-5),'Pelvis':(-6,2,8),'Chest':(-26,-2,14),'Head':(-21,-3,-8),
              'UpperArmL':(-8,54,-12),'ForearmL':(-28,0,1),'UpperArmR':(-7,-54,8),'ForearmR':(-31,1,-5)}
        exhale={**roar,'hip':(1,-5,-11),'Chest':(-9,0,8),'Head':(-8,0,-4)}
        self.clip('BellWave',2.32,[(0,braced),(.21,curl),(.36,{**curl,'Chest':(35,8,-15)}),
                  (.41,curl),(.47,roar),(.59,roar),(.72,exhale),(.85,brace),(1,braced)])
        coil={**braced,'hip':(-6,4,-15),'Chest':(8,-11,29),'Pelvis':(2,3,14),
              'UpperArmL':(-21,7,19),'ForearmL':(-69,0,12),'feet':stance}
        check={**coil,'hip':(6,-9,-13),'Chest':(18,13,-35),'Pelvis':(5,8,-17),'Head':(-6,-6,21),
               'UpperArmL':(-39,3,-6),'ForearmL':(-66,0,10),'shield':(12,-5,20)}
        self.clip('ShoulderCheck',1.06,[(0,braced),(.24,coil),(.35,coil),(.415,check),
                  (.475,check),(.60,{**check,'hip':(4,-6,-16)}),(.79,brace),(1,braced)])

        # Low target: lower the hips onto the flexed lead knee and direct the blade
        # below the grip. At full extension the tip reaches just above the target's shin.
        def low(pose,grip,line,angle,dip):
            x,y,z=pose.get('hip',(0,0,0))
            cx,cy,cz=pose.get('Chest',GUARD['Chest'])
            return {**pose,'hip':(x,y,z-dip),'Chest':(cx+angle,cy,cz),
                    'Head':(10,-1,-cz*.45),'feet':{'L':((16,-15,10),0),'R':((-15,14,10),-4)},
                    'sword':(grip,line)}
        ready=low(wind,(-45,-1,119),(-.83,.38,.41),12,6)
        sweep1=low(strike,(-40,-35,99),(-.51,-.63,-.58),15,13)
        sweep2=low(cross,(-9,-41,87),(.51,-.64,-.56),16,15)
        finish=low(follow,(1,-28,89),(.83,.14,-.54),9,7)
        self.clip('LowCut',.60,[(0,{}),(.18,ready),(.28,ready),(.39,sweep1),(.52,sweep2),
                  (.66,finish),(.80,finish),(1,{})])
        backward=low(reverse_wind,(1,-19,103),(.83,.32,-.27),12,7)
        backhit=low(reverse_hit,(-23,-38,91),(.24,-.76,-.59),20,15)
        out=low(reverse_end,(-46,-14,106),(-.83,.06,-.54),12,8)
        self.clip('LowReturnCut',.75,[(0,finish),(.18,backward),(.28,backward),
                  (.41,backhit),(.53,out),(.69,out),(1,{})])
        plunging=low(draw,(-39,3,114),(-.70,.66,.31),11,4)
        arc=low(strike,(-33,-35,91),(-.27,-.80,-.54),17,15)
        hook=low(follow,(-1,-36,87),(.66,-.48,-.58),21,16)
        recover=low(rise,(1,-29,131),(.80,.10,.58),10,6)
        self.clip('LowOathCut',.85,[(0,{}),(.21,plunging),(.32,plunging),(.44,arc),
                  (.56,hook),(.70,recover),(.83,recover),(1,{})])
