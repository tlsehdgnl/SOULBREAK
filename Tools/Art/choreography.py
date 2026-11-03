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
        rotation=original.rotation_difference(direction)
        center=bone.head.copy()
        bone.matrix=(Matrix.Translation(center)@rotation.to_matrix().to_4x4()@
                     Matrix.Translation(-center)@bone.matrix)
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
        for fraction, pose in beats:
            self.key(1+round(fraction*frames),pose)
        for curve in action.fcurves:
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
