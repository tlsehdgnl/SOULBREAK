#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Data/SBCombatData.h"

namespace
{
struct FTarget
{
    int32 Last=-1, Phase=1; float HP=400, Arm=90; bool Broken=false;
    ESBHitResult Hit(int32 Id,float Amount,bool Part)
    {
        return SBCombat::Resolve(Id,Last,Amount,Part,HP,Arm,Broken,Phase);
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSBDedup,"SoulBreak.Combat.Dedup",EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FSBDedup::RunTest(const FString&)
{
    FTarget T;
    for(int32 Frame=0;Frame<4;++Frame) T.Hit(1,20,false);
    TestEqual(TEXT("Repeated contact causes one hit"),T.HP,380.f);
    T.Hit(2,30,false);
    TestEqual(TEXT("Two-hit combo deals 50"),T.HP,350.f);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSBBreak,"SoulBreak.Boss.BreakOnce",EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FSBBreak::RunTest(const FString&)
{
    FTarget T; int32 Breaks=0;
    for(int32 I=1;I<=5;++I) Breaks+=T.Hit(I,20,true)==ESBHitResult::Broken;
    TestEqual(TEXT("Main HP after five arm cuts"),T.HP,300.f);
    TestEqual(TEXT("No durability remains"),T.Arm,0.f);
    TestEqual(TEXT("Arm break enters P2"),T.Phase,2);
    Breaks+=T.Hit(6,20,true)==ESBHitResult::Broken;
    TestEqual(TEXT("Single break"),Breaks,1);
    FTarget Body;
    for(int32 I=1;I<=10;++I) Body.Hit(I,20,false);
    TestEqual(TEXT("Body-only P2"),Body.Phase,2);
    TestEqual(TEXT("Body-only arm intact"),Body.Arm,90.f);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSBDeathFirst,"SoulBreak.Boss.DeathPriority",EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FSBDeathFirst::RunTest(const FString&)
{
    FTarget T; T.HP=1; T.Arm=1;
    TestTrue(TEXT("Lethal blow is death"),T.Hit(1,20,true)==ESBHitResult::Death);
    TestEqual(TEXT("No phase transition"),T.Phase,1);
    TestFalse(TEXT("No break"),T.Broken);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSBArmorRoutes,"SoulBreak.Boss.IndependentArmorAndCounter",EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FSBArmorRoutes::RunTest(const FString&)
{
    int32 Last=-1, Phase=1;
    float HP=400, Shield=75, Knee=65;
    bool bShield=false,bKnee=false;
    auto HitShield=[&](int32 Id,float Damage,float Scale) {
        return SBCombat::ResolvePart(Id,Last,Damage,ESBArmorPart::Shield,HP,Shield,bShield,Phase,Scale);
    };
    HitShield(1,20,1.5f);
    TestEqual(TEXT("counter increases shield damage only"),Shield,45.f);
    TestEqual(TEXT("base HP damage even during exposure"),HP,380.f);
    SBCombat::ResolvePart(1,Last,20,ESBArmorPart::Knee,HP,Knee,bKnee,Phase);
    TestEqual(TEXT("same swing cannot damage another body part"),Knee,65.f);
    TestTrue(TEXT("shield breaks independently"),HitShield(2,45,1)==ESBHitResult::Broken);
    TestTrue(TEXT("shield flag set"),bShield);
    TestEqual(TEXT("shield alone leaves phase one active"),Phase,1);
    TestTrue(TEXT("body blow on broken shield"),HitShield(3,20,1)==ESBHitResult::Body);
    HP=220;
    const ESBHitResult Cross=SBCombat::ResolvePart(4,Last,65,ESBArmorPart::Knee,HP,Knee,bKnee,Phase);
    TestTrue(TEXT("crossing health threshold still breaks knee"),Cross==ESBHitResult::Broken && bKnee);
    TestEqual(TEXT("simultaneous HP transition applies exactly once"),Phase,2);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSBDefense,"SoulBreak.Combat.WindowsAndResources",EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FSBDefense::RunTest(const FString&)
{
    const USBCombatData* D=GetDefault<USBCombatData>();
    for(const auto* W : {&D->Evade,&D->Parry})
    {
        TestFalse(TEXT("Early contact"),SBCombat::InWindow(W->Open-.001f,*W));
        TestTrue(TEXT("Start included"),SBCombat::InWindow(W->Open,*W));
        TestFalse(TEXT("End excluded"),SBCombat::InWindow(W->Close,*W));
        for(float Fps : {30.f,60.f})
        {
            int32 ActiveFrames=0;
            for(int32 I=0;I<=Fps;++I) ActiveFrames+=SBCombat::InWindow(I/Fps,*W);
            TestTrue(TEXT("Defense available at 30 and 60 FPS"),ActiveFrames>0);
        }
    }
    float S=100;
    SBCombat::Spend(S,D->Cut.Cost); SBCombat::Spend(S,D->ReturnCut.Cost);
    TestEqual(TEXT("Combo costs 35"),S,65.f);
    TestFalse(TEXT("Reject unavailable stamina"),SBCombat::Spend(S,66.f));
    TestEqual(TEXT("No partial cost"),S,65.f);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSBPresentationTiming,"SoulBreak.Combat.PresentationTiming",EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FSBPresentationTiming::RunTest(const FString&)
{
    // A designer can change windup/recovery without moving the visible contact off the hit.
    for (float Windup : {.25f,.65f,1.2f})
    {
        const float End=Windup+.15f, Duration=End+.8f;
        TestEqual(TEXT("Contact exactly at damage time"),SBCombat::AttackPoseTime(Windup,Windup,End,Duration,.454f,.62f),.454f);
        TestEqual(TEXT("Follow-through at active end"),SBCombat::AttackPoseTime(End,Windup,End,Duration,.454f,.62f),.62f);
        for (float Fps : {30.f,60.f,120.f})
        {
            float Previous=0;
            for (float T=0;T<Duration+.1f;T+=1.f/Fps)
            {
                const float Position=SBCombat::AttackPoseTime(T,Windup,End,Duration,.454f,.62f);
                TestTrue(TEXT("Pose advances monotonically and stays in clip"),Position>=Previous && Position<=1.f);
                Previous=Position;
            }
        }
    }
    for (auto Action : {ESBKnightAction::SwordSweep,ESBKnightAction::Bash,ESBKnightAction::ShieldCharge,ESBKnightAction::ShoulderCheck})
        TestTrue(TEXT("Contact attacks allow parry"),SBCombat::CanParry(Action));
    for (auto Action : {ESBKnightAction::Stomp,ESBKnightAction::BellWave,ESBKnightAction::Idle,ESBKnightAction::Stagger})
        TestFalse(TEXT("Waves and nonattacks cannot be parried"),SBCombat::CanParry(Action));
    for (auto Action : {ESBKnightAction::Stomp,ESBKnightAction::BellWave,ESBKnightAction::ShieldCharge})
    {
        TestTrue(TEXT("Heavy recovery leaves time for two cuts"),SBCombat::RecoveryDuration(Action,.4f)>=1.35f);
        TestEqual(TEXT("Longer designer recovery remains intact"),SBCombat::RecoveryDuration(Action,2.f),2.f);
    }
    return true;
}
#endif
