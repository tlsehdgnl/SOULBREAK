#include "Tests/SBScenarioAudit.h"
#if !UE_BUILD_SHIPPING
#include "Boss/SBKnight.h"
#include "Combat/SBTrainingDummy.h"
#include "Core/SBGameMode.h"
#include "Player/SBHero.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

namespace SBAudit
{
    // These values intentionally outlive OpenLevel; no pointer to an actor/world survives.
    struct FRun
    {
        TArray<FString> Results;
        int32 Reloads=0, Victories=0, Defeats=0;
        double ReloadStarted=0, MaxReload=0;
        bool bDone=false;
    };
    FRun Run;
    void Checkpoint(const FString& Name)
    {
        Run.Results.Add(FString::Printf(TEXT("{\"check\":\"%s\",\"passed\":true}"),*Name));
        UE_LOG(LogTemp,Display,TEXT("SBAudit PASS %s"),*Name);
    }
    void End(const FString& Failure=FString())
    {
        if (Run.bDone) return;
        Run.bDone=true;
        FString Path;
        if (!FParse::Value(FCommandLine::Get(),TEXT("SBAuditOut="),Path)) Path=FPaths::ProjectSavedDir()/TEXT("QA/encounter.json");
        IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
        FString JSON=FString::Printf(TEXT("{\n\"passed\":%s,\"failure\":\"%s\",\"victory_retries\":%d,\"defeat_retries\":%d,\"max_reload_to_input_seconds\":%.5f,\n\"method\":\"PlayerController simulated keys; teleports and injected incoming/phase/lethal hits are deterministic test fixtures. AI, hit resolver, stamina, map reload, move component and Enhanced Input are live.\",\n\"checks\":[%s]\n}\n"),
            Failure.IsEmpty()?TEXT("true"):TEXT("false"),*Failure,Run.Victories,Run.Defeats,Run.MaxReload,*FString::Join(Run.Results,TEXT(",\n")));
        bool bWrote=FFileHelper::SaveStringToFile(JSON,*Path,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        UE_LOG(LogTemp,Display,TEXT("SBAudit END passed=%d failure=%s path=%s"),Failure.IsEmpty() && bWrote,*Failure,*Path);
        FPlatformMisc::RequestExitWithStatus(false,Failure.IsEmpty() && bWrote ? 0 : 1);
    }
}
#endif
ASBScenarioAudit::ASBScenarioAudit()
{
#if !UE_BUILD_SHIPPING
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickGroup=TG_PostUpdateWork;
#endif
}
void ASBScenarioAudit::Tick(float Dt)
{
    Super::Tick(Dt);
#if !UE_BUILD_SHIPPING
    using namespace SBAudit;
    if (Run.bDone) return;
    Clock+=Dt;
    ASBGameMode* G=GetWorld()->GetAuthGameMode<ASBGameMode>();
    auto* PC=GetWorld()->GetFirstPlayerController();
    if (!G || !PC || !G->Hero || !G->Knight || !G->Dummy)
    {
        if (Clock>8) End(TEXT("Game mode did not spawn the four required actors"));
        return;
    }
    ASBHero* H=G->Hero; ASBKnight* K=G->Knight;
    auto Key=[&](const FKey& Kb,bool Down) { PC->InputKey(FInputKeyEventArgs::CreateSimulated(Kb,Down?IE_Pressed:IE_Released,Down?1.f:0.f)); };
    for (FKey Kb:Releases) Key(Kb,false);
    Releases.Reset();
    auto Tap=[&](const FKey& Kb) {Key(Kb,true);Releases.Add(Kb);};
    auto Next=[&](int32 To){Step=To;Clock=0;};
    auto Require=[&](bool Good,const TCHAR* What) {
        if (!Good) End(FString::Printf(TEXT("step %d, reload %d: %s"),Step,Run.Reloads,What));
        return Good;
    };
    if (Clock>(Step==14 ? 40.f : 6.f))
    {
        End(FString::Printf(TEXT("Timeout at step %d reload %d: hero action %d, boss action %d, seen %d, dummy hp %.0f hero %.0f boss %.0f"),
            Step,Run.Reloads,int32(H->Action),int32(K->Action),Observed,G->Dummy->Health,H->Health,K->Health));return;
    }
    auto Place=[&](FVector XY,float Yaw){
        XY.Z=H->GetActorLocation().Z; H->GetCharacterMovement()->StopMovementImmediately();
        H->SetActorLocationAndRotation(XY,FRotator(0,Yaw,0),false,nullptr,ETeleportType::TeleportPhysics);
        PC->SetControlRotation(FRotator(-8,Yaw,0));
    };
    switch(Step)
    {
    case 0:
    {
        if (!H->InputComponent || Clock<.08f) return;
        int32 BossCount=0;for(TActorIterator<ASBKnight> I(GetWorld());I;++I) ++BossCount;
        if (!Require(BossCount==1 && G->Encounter==ESBEncounter::Approach && K->Health==400 && !K->bArmBroken && K->ArmHealth==90 && K->Phase==1 && !K->bEncounterActive && K->PatternsStarted==0 && H->Health==100 && H->Stamina==100 && !H->bLockedOn && !H->bOathReady && G->Dummy->Health==100,TEXT("fresh map failed reset checks"))) return;
        StartPosition=H->GetActorLocation();Key(EKeys::W,true); Next(1);return;
    }
    case 1:
    {
        if (FVector::Dist2D(H->GetActorLocation(),StartPosition)<12) return;
        Key(EKeys::W,false);
        if (Run.Reloads>0)
        {
            const double Seconds=FPlatformTime::Seconds()-Run.ReloadStarted;
            Run.MaxReload=FMath::Max(Run.MaxReload,Seconds);
            if (!Require(Seconds<=3.0,TEXT("more than 3 wall-clock seconds to regain movement after retry"))) return;
            Checkpoint(FString::Printf(TEXT("reload %02d fresh HP arm phase AI input; %.3fs to W movement"),Run.Reloads,Seconds));
            if (Run.Reloads==20) {End();return;}
            Next(10);return;
        }
        Tap(EKeys::Tab);Next(2);return;
    }
    case 2:
        if (!H->bLockedOn || Clock<.09f) return;
        Tap(EKeys::Tab);Next(3);return;
    case 3:
        if (H->bLockedOn) return;
        Checkpoint(TEXT("W walks; Tab toggles torso lock on and off"));
        Place(G->Dummy->GetActorLocation()+FVector(0,-112,0),90);
        Tap(EKeys::LeftMouseButton);Next(4);return;
    case 4:
        if (H->Action!=ESBHeroAction::Cut || H->ActionElapsed<.43f) return;
        if (!Require(G->Dummy->Health==80 && FMath::IsNearlyEqual(H->Stamina,85.f),TEXT("first live swing did not cause exactly 20 damage at 15 stamina"))) return;
        Checkpoint(TEXT("left mouse hits dummy once for 20 across repeated traces"));
        Tap(EKeys::LeftMouseButton);Next(5);return;
    case 5:
        if (H->Action!=ESBHeroAction::ReturnCut || H->ActionElapsed<.45f) return;
        if (!Require(G->Dummy->Health==50 && FMath::IsNearlyEqual(H->Stamina,65.f),TEXT("buffered second hit did not produce 50 total damage and 35 total cost"))) return;
        Checkpoint(TEXT("buffered left mouse combo damage 50 stamina 35"));Next(6);return;
    case 6:
        if (H->Action!=ESBHeroAction::Ready) return;
        StartPosition=H->GetActorLocation();Tap(EKeys::SpaceBar);Next(7);return;
    case 7:
        if (H->Action!=ESBHeroAction::Evade || H->ActionElapsed<.12f) return;
        H->ReceivePattern(5,false);
        if (!Require(H->Health==100 && H->DodgedHits==1,TEXT("in-window dodge took damage"))) return;
        Next(8);return;
    case 8:
        if (H->Action!=ESBHeroAction::Ready) return;
        if (!Require(FMath::Abs(FVector::Dist2D(StartPosition,H->GetActorLocation())-280.f)<5.f,TEXT("unobstructed dodge travel differs from 280cm"))) return;
        H->ReceivePattern(5,false);
        if (!Require(H->Health==95,TEXT("out-of-window hit ignored"))) return;
        Checkpoint(TEXT("Space dodge travelled 280cm; injected incoming hits inside and outside invulnerability matched"));
        Next(21);return;
    case 21:
        if (H->Action!=ESBHeroAction::Ready) return;
        Place(G->Dummy->GetActorLocation()+FVector(0,-105,0),90);
        Tap(EKeys::RightMouseButton);Next(22);return;
    case 22:
        if (H->Action!=ESBHeroAction::Parry || H->ActionElapsed<.08f) return;
        H->ReceivePattern(22,true);
        if (!Require(H->Health==95 && H->bOathReady && H->SuccessfulParries==1,TEXT("right-click parry failed to grant oath"))) return;
        Next(23);return;
    case 23:
        if (H->Action!=ESBHeroAction::Ready) return;
        Tap(EKeys::E);Next(24);return;
    case 24:
        if (H->Action!=ESBHeroAction::OathCut || H->ActionElapsed<.54f) return;
        if (!Require(G->Dummy->Health==10 && !H->bOathReady,TEXT("E did not consume parry charge and deal 40"))) return;
        Checkpoint(TEXT("right mouse parried simulated sword; E consumed charge and struck dummy for 40"));
        H->Health=100;Next(10);return;
    case 10:
        // Wait over one pattern impact interval before crossing the gate on each new world.
        if (Clock<.85f || H->Action!=ESBHeroAction::Ready) return;
        if (!Require(H->Health==100 && !K->bEncounterActive,TEXT("stale encounter state while in approach"))) return;
        Place(K->GetActorLocation()+K->GetActorForwardVector()*122,0);
        Next(11);return;
    case 11:
        if (G->Encounter!=ESBEncounter::Fighting || K->Action!=ESBKnightAction::SwordSweep || K->PatternElapsed>.25f) return;
        if (Run.Reloads<2)
        {
            const bool Arm=Run.Reloads==0;
            for (int32 I=1;I<=(Arm?5:10);++I) K->ApplySwordHit(100+I,20,Arm);
            if (!Require(K->Phase==2 && K->PhaseChanges==1 && K->BreakCount==(Arm?1:0) && K->Health==(Arm?300:200) && K->ArmHealth==(Arm?0:90),TEXT("wrong branch state after deterministic sword strikes"))) return;
            Checkpoint(Arm?TEXT("5 arm strikes: boss 300, arm 0, one break and P2"):TEXT("10 body strikes: boss 200, arm 90, P2"));
            Next(12);return;
        }
        Next(15);return;
    case 12:
        if (Clock<.80f) return;
        if (!Require(H->Health==100,TEXT("interrupted sword still caused damage during transition"))) return;
        Checkpoint(TEXT("cancelled windup produced no damage at scheduled impact"));
        Next(14);return;
    case 14:
    {
        // Keep AI in range and replenish its live target to observe ten complete selections.
        H->Health=100;
        const bool Pattern=K->Action==ESBKnightAction::SwordSweep || K->Action==ESBKnightAction::Bash || K->Action==ESBKnightAction::Stomp;
        if (!Pattern || PreviousGeneration==K->AttackGeneration) return;
        PreviousGeneration=K->AttackGeneration; ++Observed;
        if (Observed==1 && !Require(K->Action==ESBKnightAction::Stomp,TEXT("first in-range P2 attack should be stomp"))) return;
        bSawSword|=K->Action==ESBKnightAction::SwordSweep;bSawBash|=K->Action==ESBKnightAction::Bash;bSawStomp|=K->Action==ESBKnightAction::Stomp;
        if (Observed<10) return;
        if (!Require(bSawSword==(Run.Reloads==1) && bSawBash && bSawStomp,TEXT("ten P2 patterns did not match available limbs"))) return;
        Checkpoint(Run.Reloads==0 ? TEXT("broken arm: 10 real AI selections saw stomp and bash; zero sword") : TEXT("intact arm: 10 real AI selections saw stomp, bash, sword"));
        Next(15);return;
    }
    case 15:
        if ((Run.Reloads%2)==0) K->ApplySwordHit(1000,1000,false);
        else H->ReceivePattern(1000,false);
        Next(16);return;
    case 16:
    {
        bool Win=Run.Reloads%2==0;
        if (G->Encounter!=(Win?ESBEncounter::Victory:ESBEncounter::Defeat)) return;
        if (Win) ++Run.Victories; else ++Run.Defeats;
        ++Run.Reloads;Run.ReloadStarted=FPlatformTime::Seconds();
        Tap(EKeys::R);Next(17);return;
    }
    default: return; // OpenLevel will replace this actor.
    }
#endif
}
