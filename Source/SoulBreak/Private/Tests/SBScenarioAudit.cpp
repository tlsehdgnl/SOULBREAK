#include "Tests/SBScenarioAudit.h"
#include "Camera/CameraActor.h"
#if !UE_BUILD_SHIPPING
#include "Boss/SBKnight.h"
#include "Camera/PlayerCameraManager.h"
#include "Combat/SBTrainingDummy.h"
#include "Core/SBGameMode.h"
#include "Player/SBHero.h"
#include "Components/SkeletalMeshComponent.h"
#include "EngineUtils.h"
#include "Engine/GameViewportClient.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Slate/SceneViewport.h"
#include "Widgets/SViewport.h"

namespace SBAudit
{
    // These values intentionally outlive OpenLevel; no pointer to an actor/world survives.
    struct FTiming
    {
        double Press=0, Observed=0;
        uint64 PressFrame=0, ObservedFrame=0;
        float PressAtActionTime=0;
        FString ToJson(const TCHAR* Label) const
        {
            if (!ObservedFrame) return FString::Printf(TEXT("{\"case\":\"%s\",\"observed\":false}"),Label);
            return FString::Printf(TEXT("{\"case\":\"%s\",\"observed\":true,\"press_game_s\":%.6f,\"press_at_previous_action_s\":%.6f,\"first_observed_game_s\":%.6f,\"frames\":%llu,\"sim_ms\":%.3f}"),
                Label,Press,PressAtActionTime,Observed,static_cast<unsigned long long>(ObservedFrame-PressFrame),1000.*(Observed-Press));
        }
        void Requested(const ASBHero& H)
        {
            Press=H.GetWorld()->GetTimeSeconds();PressFrame=GFrameCounter;PressAtActionTime=H.ActionElapsed;
        }
        void Started(const ASBHero& H)
        {
            if (!ObservedFrame) { Observed=H.GetWorld()->GetTimeSeconds();ObservedFrame=GFrameCounter; }
        }
    };
    struct FRun
    {
        TArray<FString> Results;
        FTiming Combo, Dodge, Parry;
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
        JSON.RemoveFromEnd(TEXT("}\n"));
        JSON+=FString::Printf(TEXT(",\n\"input_measurement\":\"Engine simulation time between a synthetic key press and the first post-update tick observing its action; excludes physical input, rendering and display latency.\",\n\"timings\":[%s,%s,%s]\n}\n"),
            *Run.Combo.ToJson(TEXT("early_second_click")),*Run.Dodge.ToJson(TEXT("buffered_dodge")),*Run.Parry.ToJson(TEXT("late_parry")));
        if (FParse::Param(FCommandLine::Get(),TEXT("SBAuditViewportLook")))
        {
            JSON=FString::Printf(TEXT("{\n\"scenario\":\"viewport mouse look\",\"passed\":%s,\"failure\":\"%s\",\n\"method\":\"Synthetic unbuttoned raw pointer motion sent to the live Slate viewport. The engine accumulates hardware-axis samples and applies gameplay bindings. Rotation is sampled from PlayerCameraManager. Physical mouse and display latency are not measured.\",\n\"checks\":[%s]\n}\n"),
                Failure.IsEmpty()?TEXT("true"):TEXT("false"),*Failure,*FString::Join(Run.Results,TEXT(",\n")));
        }
        bool bWrote=FFileHelper::SaveStringToFile(JSON,*Path,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        UE_LOG(LogTemp,Display,TEXT("SBAudit END passed=%d failure=%s path=%s"),Failure.IsEmpty() && bWrote,*Failure,*Path);
#if WITH_EDITOR
        // PIE owns a world inside the running editor. Let its caller end that session normally.
        if (GIsEditor && !IsRunningGame()) return;
#endif
        FPlatformMisc::RequestExitWithStatus(false,Failure.IsEmpty() && bWrote ? 0 : 1);
    }
}
#endif
ASBScenarioAudit::ASBScenarioAudit()
{
#if !UE_BUILD_SHIPPING
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bTickEvenWhenPaused=FParse::Param(FCommandLine::Get(),TEXT("SBAuditViewportLook"));
    PrimaryActorTick.TickGroup=TG_PostUpdateWork;
#endif
}
#if !UE_BUILD_SHIPPING
// A separate scenario so regular headless combat tests can still run without a Slate viewport.
void ASBScenarioAudit::TickViewportLook(APlayerController& PC, ASBGameMode& Game)
{
    using namespace SBAudit;
    UGameViewportClient* Client=GetWorld()->GetGameViewport();
    FSceneViewport* Viewport=Client ? Client->GetGameViewport() : nullptr;
    if (!Viewport || !PC.PlayerCameraManager || !Game.Hero->InputComponent)
    {
        if (Clock>4.f) End(TEXT("No game viewport, player camera or input component"));
        return;
    }
    const FRotator View=PC.PlayerCameraManager->GetCameraRotation();
    auto Moved=[&](const FVector2D& Pixels)
    {
        // This enters before hardware mouse samples are accumulated, mapped and consumed.
        const FVector2D Center=Viewport->GetCachedGeometry().GetAbsolutePositionAtCoordinates(FVector2f(.5f,.5f));
        const TSet<FKey> NoButtons;
        const FPointerEvent Event(FSlateApplication::CursorPointerIndex,Center,Center,Pixels,NoButtons,FModifierKeysState());
        Client->GetGameViewportWidget()->OnMouseMove(Viewport->GetCachedGeometry(),Event);
    };
    auto Advance=[&] { ++Step; Clock=0; };
    const FRotator Diff=(View-LookBaseline).GetNormalized();
    if (FParse::Param(FCommandLine::Get(),TEXT("SBAuditUnfocusedLook")))
    {
        if (Clock<.3f) return;
        if (FApp::HasFocus() || !Viewport->HasMouseCapture() || PC.bShowMouseCursor)
        {
            End(TEXT("Background probe requires an inactive app with a captured gameplay viewport"));return;
        }
        if (Step==0)
        {
            LookBaseline=View;
            Moved({48,-32});
            Advance();return;
        }
        if (!View.Equals(LookBaseline,.05)) {End(TEXT("Background pointer motion rotated the game camera"));return;}
        Checkpoint(TEXT("unfocused app ignored captured viewport pointer motion on both axes"));
        End();return;
    }
    switch (Step)
    {
    case 0:
        if (Clock<.3f) return;
        if (!Viewport->HasMouseCapture() || PC.bShowMouseCursor)
        {
            End(TEXT("Play viewport failed to capture the mouse at startup"));return;
        }
        LookBaseline=View;
        Moved({48,-32});
        Advance();return;
    case 1:
        if (Clock<.15f) return;
        if (Diff.Yaw<1 || Diff.Pitch<1) {End(TEXT("Unbuttoned viewport pointer motion failed to rotate the player camera on both axes"));return;}
        Checkpoint(FString::Printf(TEXT("free look from viewport pointer: yaw %.2f, pitch %.2f degrees"),Diff.Yaw,Diff.Pitch));
        Game.ToggleHelp();
        Advance();return;
    case 2:
        if (!Game.bHelpOpen || !PC.bShowMouseCursor) {End(TEXT("Help did not return the cursor"));return;}
        LookBaseline=View;
        Moved({40,-20});
        Advance();return;
    case 3:
        if (!View.Equals(LookBaseline,.1)) {End(TEXT("Help pointer moved the gameplay camera"));return;}
        Game.ToggleHelp();
        Advance();return;
    case 4:
        if (Clock<.2f) return;
        if (Game.bHelpOpen || PC.bShowMouseCursor || !Viewport->HasMouseCapture()) {End(TEXT("Resume failed to recapture the mouse"));return;}
        LookBaseline=View;
        Moved({-48,32});
        Advance();return;
    case 5:
        if (Clock<.15f) return;
        if (Diff.Yaw>-1 || Diff.Pitch>-1) {End(TEXT("Viewport pointer did not turn and tilt the camera after resume"));return;}
        Checkpoint(FString::Printf(TEXT("help releases cursor; resumed viewport look: yaw %.2f, pitch %.2f degrees"),Diff.Yaw,Diff.Pitch));
        PC.InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::Tab,IE_Pressed,1));
        Advance();return;
    case 6:
        PC.InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::Tab,IE_Released,0));
        if (Clock<1.f) return; // The knight is idle before crossing the encounter line.
        if (!Game.Hero->bLockedOn) {End(TEXT("Tab did not establish a stationary lock target"));return;}
        LookBaseline=View;
        Advance();return;
    case 7:
        if (++LookSamples<=12) {Moved({36,-18});return;}
        if (Clock<.6f) return;
        if (!Game.Hero->bLockedOn || Diff.Yaw<1 || Diff.Yaw>50 || Diff.Pitch<1 || Diff.Pitch>30)
        {
            End(FString::Printf(TEXT("Locked pointer framing out of range: yaw %.2f pitch %.2f"),Diff.Yaw,Diff.Pitch));return;
        }
        Checkpoint(FString::Printf(TEXT("locked viewport pointer kept target and adjusted framing: yaw %.2f, pitch %.2f degrees"),Diff.Yaw,Diff.Pitch));
        End();return;
    }
}
#endif
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
    if (PrimaryActorTick.bTickEvenWhenPaused) {TickViewportLook(*PC,*G);return;}
    auto Key=[&](const FKey& Kb,bool Down) { PC->InputKey(FInputKeyEventArgs::CreateSimulated(Kb,Down?IE_Pressed:IE_Released,Down?1.f:0.f)); };
    for (FKey Kb:Releases) Key(Kb,false);
    Releases.Reset();
    auto Tap=[&](const FKey& Kb) {Key(Kb,true);Releases.Add(Kb);};
    auto Next=[&](int32 To){Step=To;Clock=0;};
    auto Require=[&](bool Good,const TCHAR* What) {
        if (!Good) End(FString::Printf(TEXT("step %d, reload %d: %s"),Step,Run.Reloads,What));
        return Good;
    };
    if (Clock>(Step==14 || Step==79 ? 40.f : 6.f))
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
        if (!Require(!K->bShieldBroken && !K->bKneeBroken && K->ShieldHealth==75 && K->KneeHealth==65 &&
            K->BreakCount==0 && H->SelectedPart==ESBArmorPart::Body,TEXT("armor or target selection persisted after reload"))) return;
        if (Run.Reloads==0 && FParse::Param(FCommandLine::Get(),TEXT("SBAuditArmorAssets")))
        {
            const auto* Mesh=K->GetMesh();
            if (!Require(Mesh->GetBoneIndex(TEXT("ShieldPlate"))!=INDEX_NONE && Mesh->GetBoneIndex(TEXT("KneePlateL"))!=INDEX_NONE,
                TEXT("current knight mesh lacks the authored independent shield or knee bone"))) return;
            Checkpoint(TEXT("knight skeletal mesh exposes separate shield and knee break bones"));
        }
        if (Run.Reloads==0 && FParse::Param(FCommandLine::Get(),TEXT("SBAuditLook")))
        {
            if (!Require(FApp::HasFocus() && GetWorld()->TimeSeconds<.20f,TEXT("for startup mouse audit run focused or with -benchmark"))) return;
            StartPosition.X=PC->GetControlRotation().Yaw;
            PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseX,IE_Axis,8.f,1));
            Next(50);return;
        }
        StartPosition=H->GetActorLocation();Key(EKeys::W,true); Next(1);return;
    }
    case 50:
    {
        float Change=FMath::FindDeltaAngleDegrees(StartPosition.X,double(PC->GetControlRotation().Yaw));
        if (FMath::Abs(Change)<.005f && Clock<.05f) return;
        if (!Require(Change>.005f && Change<16.f && GetWorld()->TimeSeconds<.25f,TEXT("first intentional mouse sample did not rotate immediately"))) return;
        StartPosition.Y=PC->GetControlRotation().Pitch;
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseY,IE_Axis,1600.f,1));
        Next(51);return;
    }
    case 51:
        if (Clock<.035f) return;
        if (!Require(FMath::Abs(FMath::FindDeltaAngleDegrees(StartPosition.Y,double(PC->GetControlRotation().Pitch)))<.05f,TEXT("capture warp moved camera during startup"))) return;
        Checkpoint(TEXT("first normal mouse input rotated camera during startup; oversized recenter warp was discarded"));
        StartPosition=H->GetActorLocation();Key(EKeys::W,true);Next(1);return;
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
        if (H->Action!=ESBHeroAction::Cut || H->ActionElapsed<.15f) return;
        if (!Require(H->ActionElapsed<.4f,TEXT("quick second click did not precede the old combo window"))) return;
        Run.Combo.Requested(*H);Tap(EKeys::LeftMouseButton);Next(40);return;
    case 40:
        if (H->ActionElapsed<.39f) return;
        if (!Require(H->Action==ESBHeroAction::Cut && G->Dummy->Health==80 && FMath::IsNearlyEqual(H->Stamina,85.f),TEXT("early combo charged or began before first swing ended"))) return;
        Checkpoint(TEXT("early second click persisted; first swing dealt 20 and spent 15 without shortening recovery"));
        Next(5);return;
    case 5:
        if (H->Action!=ESBHeroAction::ReturnCut) return;
        Run.Combo.Started(*H);
        if (H->ActionElapsed<.282f) return;
        if (!Require(FMath::IsNearlyEqual(H->Stamina,65.f),TEXT("second cut should spend 20 exactly once"))) return;
        StartPosition=H->GetActorLocation();
        Tap(EKeys::LeftMouseButton);Run.Dodge.Requested(*H);Key(EKeys::SpaceBar,true);Next(60);return;
    case 60:
        if (H->ActionElapsed<.34f) return;
        if (!Require(H->Action==ESBHeroAction::ReturnCut && H->ActionElapsed<H->CombatData->ReturnCut.Close && H->Stamina==65.f,TEXT("buffered dodge displaced an active hit or spent stamina early"))) return;
        ExpectedDefenseStart=GetWorld()->GetTimeSeconds()+H->CombatData->ReturnCut.Close-H->ActionElapsed;
        Tap(EKeys::LeftMouseButton); // A later low-priority press cannot displace the queued defense.
        Next(7);return;
    case 7:
        if (H->Action!=ESBHeroAction::Evade) return;
        Run.Dodge.Started(*H);
        if (H->ActionElapsed<.12f) return;
        if (!Require(FMath::Abs((GetWorld()->GetTimeSeconds()-H->ActionElapsed)-ExpectedDefenseStart)<=Dt+.01f,TEXT("dodge did not start on the first frame after attack contact closed"))) return;
        if (!Require(H->Stamina==43.f && G->Dummy->Health==50,TEXT("final sword contact missing, or double stamina charge"))) return;
        Checkpoint(TEXT("buffered two cuts dealt 50 and consumed 35; dodge took priority and consumed 22 only after the active window closed"));
        H->ReceivePattern(5,false);
        if (!Require(H->Health==100 && H->DodgedHits==1,TEXT("in-window dodge took damage"))) return;
        Next(8);return;
    case 8:
        if (Clock<.63f) return;
        if (!Require(H->Action==ESBHeroAction::Ready,TEXT("holding Space repeated the dodge without another press"))) return;
        Key(EKeys::SpaceBar,false);
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
        if (H->Action!=ESBHeroAction::Parry || H->ActionElapsed<.39f) return;
        ExpectedDefenseStart=GetWorld()->GetTimeSeconds()+H->CombatData->Parry.Duration-H->ActionElapsed;
        Tap(EKeys::E);Next(24);return;
    case 24:
        if (H->Action!=ESBHeroAction::OathCut || H->ActionElapsed<.54f) return;
        if (!Require(FMath::Abs((GetWorld()->GetTimeSeconds()-H->ActionElapsed)-ExpectedDefenseStart)<=Dt+.01f,TEXT("queued skill shortened parry cooldown or waited past recovery"))) return;
        if (!Require(G->Dummy->Health==10 && !H->bOathReady,TEXT("E did not consume parry charge and deal 40"))) return;
        Checkpoint(TEXT("right mouse parried simulated sword; queued E began at parry recovery and struck dummy for 40"));
        ExpectedDefenseStart=GetWorld()->GetTimeSeconds();
        Run.Parry.Requested(*H);Tap(EKeys::RightMouseButton);Next(25);return;
    case 25:
        if (H->Action!=ESBHeroAction::Parry) return;
        Run.Parry.Started(*H);
        if (!Require(GetWorld()->GetTimeSeconds()-ExpectedDefenseStart<=Dt*2+.01f,TEXT("late parry waited for the oath swing to finish recovery"))) return;
        Checkpoint(TEXT("fresh parry after oath impact interrupted attack recovery immediately"));
        StartPosition=H->GetActorLocation();Tap(EKeys::SpaceBar);Next(28);return;
    case 28:
        if (Clock<.61f) return;
        if (!Require(H->Action==ESBHeroAction::Ready && FVector::Dist2D(H->GetActorLocation(),StartPosition)<2,TEXT("early tap while parrying caused a delayed evade"))) return;
        Checkpoint(TEXT("early defense during parry cooldown did not execute later"));
        Key(EKeys::D,true);Key(EKeys::LeftShift,true);Next(26);return;
    case 26:
        if (Clock<.10f) return;
        if (!Require(H->GetCharacterMovement()->MaxWalkSpeed==650.f,TEXT("held Shift did not enable sprint"))) return;
        Key(EKeys::LeftShift,false);Next(27);return;
    case 27:
        if (Clock<.08f) return;
        if (!Require(H->GetCharacterMovement()->MaxWalkSpeed==450.f,TEXT("released Shift left sprint latched"))) return;
        Key(EKeys::D,false);
        Checkpoint(TEXT("held and released Shift switched 650/450 speed while movement stayed held"));
        H->Health=100;
        Place(G->Dummy->RackPoint(ESBArmorPart::SwordArm)+FVector(93,0,0),180);
        Tap(EKeys::F);Next(101);return;
    case 101:
        if (H->SelectedPart!=ESBArmorPart::SwordArm) return;
        Tap(EKeys::LeftMouseButton);Next(102);return;
    case 102:
        if (G->Dummy->RackPulse<=0) return;
        if (!Require(G->Dummy->LastRackHit==ESBArmorPart::SwordArm && K->Health==400,
            TEXT("rack hit did not resolve the focused arm independently"))) return;
        Checkpoint(TEXT("F selected the practice arm and a live swing rang the armor in the vestibule"));
        Next(10);return;
    case 10:
        // Wait over one pattern impact interval before crossing the gate on each new world.
        if (Clock<.85f || H->Action!=ESBHeroAction::Ready) return;
        if (!Require(H->Health==100 && !K->bEncounterActive,TEXT("stale encounter state while in approach"))) return;
        Place(FVector(-1230,0,95),0);
        if (Run.Reloads==0 && FParse::Param(FCommandLine::Get(),TEXT("SBAuditGateView")))
        {
            Place(FVector(-1680,0,95),0);
            Next(89);return;
        }
        Next(88);return;
    case 89:
        if (Clock<.7f) return;
        FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("QA/lit-vestibule.png"),false,false);
        Next(87);return;
    case 87:
        if (Clock<.15f) return;
        Place(FVector(-1230,0,95),0);
        Next(88);return;
    case 88:
        if (!Require(G->CanOpenDoor(),TEXT("door interaction unavailable outside threshold"))) return;
        Tap(EKeys::E);Next(90);return;
    case 90:
        if (!G->DoorIsOpen()) return;
        if (Run.Reloads==0 && FParse::Param(FCommandLine::Get(),TEXT("SBAuditGateView")))
            FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("QA/open-vestibule.png"),false,false);
        {
            FCollisionQueryParams Query(SCENE_QUERY_STAT(OpenDoorSight),false,H);
            Query.AddIgnoredActor(K);
            const FVector Eye=H->GetActorLocation()+FVector(0,0,55);
            if (!Require(!GetWorld()->LineTraceTestByChannel(Eye,K->GetActorLocation(),ECC_Visibility,Query),
                TEXT("open doorway obstructs the view from the vestibule to the knight"))) return;
        }
        if (!Require(!K->bEncounterActive && G->Encounter==ESBEncounter::Approach,TEXT("opening door started combat before crossing"))) return;
        Key(EKeys::W,true);Next(91);return;
    case 91:
        if (G->Encounter!=ESBEncounter::Introduction) return;
        if (!Require(GetWorld()->LineTraceTestByChannel(FVector(-1000,0,115),FVector(-1210,0,115),ECC_Pawn),
            TEXT("retreat possible during gate closing animation"))) return;
        if (!Require(FMath::Abs(H->GetActorLocation().X+1018.)<35.,TEXT("crossing the door displaced the player"))) return;
        Key(EKeys::W,false);
        if (!Require(!H->InputEnabled() && !K->bEncounterActive,TEXT("combat or player input active during reveal"))) return;
        Next(92);return;
    case 92:
        if (Clock<2.f) return;
        if (!Require(PC->GetViewTarget()!=H,TEXT("boss camera never took over"))) return;
        if (Run.Reloads==2 || Run.Reloads==3)
        {
            Place(K->GetActorLocation()+K->GetActorForwardVector()*435,0);
            Next(70);return;
        }
        Place(K->GetActorLocation()+K->GetActorForwardVector()*122,0);
        Next(11);return;
    case 11:
        if (G->Encounter!=ESBEncounter::Fighting || K->Action!=ESBKnightAction::SwordSweep || K->PatternElapsed>.25f) return;
        if (!Require(!G->DoorIsOpen() && GetWorld()->LineTraceTestByChannel(FVector(-1000,55,115),FVector(-1210,55,115),ECC_Visibility),
            TEXT("boss gate failed to seal at fight start"))) return;
        if (Run.Reloads>=6 && Run.Reloads<=8)
        {
            Tap(EKeys::Tab);Next(96);return;
        }
        if (Run.Reloads==4 || Run.Reloads==5)
        {
            if (Run.Reloads==5) Tap(EKeys::Tab);
            Next(94);return;
        }
        if (Run.Reloads<2)
        {
            const bool Arm=Run.Reloads==0;
            for (int32 I=1;I<=(Arm?5:10);++I) K->ApplySwordHit(100+I,20,Arm);
            if (!Require(K->Phase==2 && K->PhaseChanges==1 && K->BreakCount==(Arm?1:0) && K->Health==(Arm?300:200) && K->ArmHealth==(Arm?0:90),TEXT("wrong branch state after deterministic sword strikes"))) return;
            Checkpoint(Arm?TEXT("5 arm strikes: boss 300, arm 0, one break and P2"):TEXT("10 body strikes: boss 200, arm 90, P2"));
            Next(12);return;
        }
        Next(15);return;
    case 96:
    {
        if (!H->bLockedOn || Clock<.08f) return;
        const ESBArmorPart Part=Run.Reloads==6 ? ESBArmorPart::SwordArm : Run.Reloads==7 ? ESBArmorPart::Shield : ESBArmorPart::Knee;
        if (H->SelectedPart!=Part) {Tap(EKeys::F);Next(96);return;}
        const FVector Side=K->GetActorRightVector();
        const float Sign=FVector::DotProduct(K->PartPoint(Part)-K->GetActorLocation(),Side)>=0 ? 1.f : -1.f;
        Place(K->GetActorLocation()+Side*Sign*100.,0);
        Tap(EKeys::LeftMouseButton);Next(97);return;
    }
    case 97:
        if (K->Health>=400) return;
        if (!Require(K->Health==380 && K->GetPartHealth(H->SelectedPart)==K->GetPartMaxHealth(H->SelectedPart)-20,
            TEXT("lateral strike missed selected armor or duplicated damage"))) return;
        Checkpoint(TEXT("side-on player swing damaged selected armor exactly once"));
        Next(15);return;
    case 94:
        if (Clock<.04f) return;
        if (!Require(H->bLockedOn==(Run.Reloads==5) && H->SelectedPart==ESBArmorPart::Body,TEXT("incorrect torso targeting mode"))) return;
        Place(K->GetActorLocation()+K->GetActorForwardVector()*95,0);
        Tap(EKeys::LeftMouseButton);Next(95);return;
    case 95:
        if (K->Health>=400) return;
        if (!Require(K->Health==380 && K->ArmHealth==90 && K->ShieldHealth==75 && K->KneeHealth==65,
            TEXT("torso swing damaged armor"))) return;
        Checkpoint(Run.Reloads==4 ? TEXT("free frontal swing damaged torso only") : TEXT("locked frontal swing damaged torso only"));
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
        if (Run.Reloads==4)
        {
            K->Health=1; H->bOathReady=true;
            Place(K->GetActorLocation()+K->GetActorForwardVector()*92,0);
            if (H->Action!=ESBHeroAction::Ready) return;
            if (!H->bLockedOn) H->ToggleLock();
            Tap(EKeys::E);Next(103);return;
        }
        if ((Run.Reloads%2)==0) K->ApplySwordHit(1000,1000,false);
        else H->ReceivePattern(1000,false);
        Next(16);return;
    case 70:
        if (K->Action!=ESBKnightAction::ShieldCharge || K->PatternElapsed>.25f) return;
        StartPosition=K->GetActorLocation();
        if (Run.Reloads==3) {Next(81);return;}
        Key(EKeys::D,true);Next(71);return;
    case 71:
        if (Clock<.37f) return;
        Key(EKeys::D,false);Next(72);return;
    case 72:
        if (!K->IsPunishWindow()) return;
        if (!Require(H->Health==100 && FVector::Dist2D(StartPosition,K->GetActorLocation())>380.f,
            TEXT("sidestep failed to clear a committed charge lane"))) return;
        Checkpoint(TEXT("held D cleared a locked charge lane; knight travelled past and entered exposed recovery"));
        Tap(EKeys::Tab);Next(73);return;
    case 73:
        if (!H->bLockedOn) return;
        Tap(EKeys::F);Next(93);return;
    case 93:
        if (H->SelectedPart!=ESBArmorPart::SwordArm || Clock<.04f) return;
        Tap(EKeys::F);Next(74);return;
    case 74:
        if (H->SelectedPart!=ESBArmorPart::Shield) return;
        Place(K->GetActorLocation()+(K->PartPoint(ESBArmorPart::Shield)-K->GetActorLocation()).GetSafeNormal2D()*105,0);
        Tap(EKeys::LeftMouseButton);Next(75);return;
    case 75:
        if (K->ShieldHealth==75) return;
        if (!Require(K->ShieldHealth==45 && K->Health==380 && K->ArmHealth==90 && K->KneeHealth==65,
            TEXT("locked shield counter failed 1.5x armor-only damage"))) return;
        Checkpoint(TEXT("F selected shield; actual LMB counter dealt 20 health and 30 shield durability without double contact"));
        Tap(EKeys::F);Next(76);return;
    case 76:
        if (H->SelectedPart!=ESBArmorPart::Knee || H->Action!=ESBHeroAction::Ready) return;
        Place(K->GetActorLocation()+(K->PartPoint(ESBArmorPart::Knee)-K->GetActorLocation()).GetSafeNormal2D()*98,0);
        Tap(EKeys::LeftMouseButton);Next(77);return;
    case 77:
        if (K->KneeHealth==65) return;
        if (!Require(K->Health==360 && K->ShieldHealth==45 && K->ArmHealth==90,TEXT("aimed low cut hit an unintended part"))) return;
        Checkpoint(TEXT("next F selected knee; live low sword arc hit only the knee and body HP once"));
        K->ApplyPartHit(100,K->ShieldHealth,ESBArmorPart::Shield);
        K->ApplyPartHit(101,K->KneeHealth,ESBArmorPart::Knee);
        if (!Require(K->BreakCount==2 && K->Phase==1 && K->bShieldBroken && K->bKneeBroken &&
            K->GetCharacterMovement()->MaxWalkSpeed==150,TEXT("shield and knee breaks did not disable independent P1 armor"))) return;
        K->ApplyPartHit(102,90,ESBArmorPart::SwordArm);
        if (!Require(K->BreakCount==3 && K->Phase==2 && K->PhaseChanges==1,TEXT("three independent breaks did not trigger exactly one phase transition"))) return;
        if (FParse::Param(FCommandLine::Get(),TEXT("SBAuditArmorAssets")))
        {
            auto* Mesh=K->GetMesh();
            if (!Require(Mesh->IsBoneHiddenByName(TEXT("ShieldPlate")) && Mesh->IsBoneHiddenByName(TEXT("ShinL")) &&
                !Mesh->IsBoneHiddenByName(TEXT("HandL")) && !Mesh->IsBoneHiddenByName(TEXT("ShinR")),
                TEXT("destroyed plates did not detach independently from the surviving hand/right leg"))) return;
            Checkpoint(TEXT("shield and left lower leg detached while the hand and right shin remained visible"));
        }
        Place(K->GetActorLocation()+K->GetActorForwardVector()*790,0);
        Next(104);return;
    case 104:
        if (K->HopPhase<.35f || K->HopPhase>.65f) return;
        if (!Require(K->bKneeBroken && K->GetVelocity().Size2D()>0,TEXT("amputated knight failed to pursue on one leg"))) return;
        Checkpoint(TEXT("amputated knight entered the airborne beat while chasing"));
        if (FParse::Param(FCommandLine::Get(),TEXT("SBAuditGateView")))
        {
            const FVector Focus=K->GetActorLocation(), Eye=Focus+K->GetActorForwardVector()*420+K->GetActorRightVector()*175;
            auto* Camera=GetWorld()->SpawnActor<ACameraActor>(Eye,(Focus-Eye).Rotation());
            PC->SetViewTarget(Camera);
            Next(105);return;
        }
        Place(K->GetActorLocation()+K->GetActorForwardVector()*305,0);Next(78);return;
    case 105:
        if (Clock<.05f) return;
        FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("QA/one-foot-pursuit.png"),false,false);
        Next(106);return;
    case 106:
        if (Clock<.05f) return;
        if (auto* Camera=Cast<ACameraActor>(PC->GetViewTarget()))
        {
            PC->SetViewTarget(H);
            Camera->Destroy();
        }
        Place(K->GetActorLocation()+K->GetActorForwardVector()*305,0);Next(78);return;
    case 78:
        if (K->Action!=ESBKnightAction::BellWave || K->PatternElapsed<1.74f) return;
        if (!Require(H->Health==76 && H->SelectedPart==ESBArmorPart::Body,TEXT("wave did not hit exactly once or broken target did not reset"))) return;
        Checkpoint(TEXT("all three plates shattered; pursuit slowed to 150 and expanding wave hit a stationary target for 24 once"));
        Tap(EKeys::F);
        Place(K->GetActorLocation()+K->GetActorForwardVector()*84,0);Next(79);return;
    case 79:
        if (K->Action==ESBKnightAction::ShoulderCheck)
        {
            bSawBash=true;
            H->Health=100; // isolate the next wave from contact damage dealt by shoulder checks.
        }
        if (!Require(K->Action!=ESBKnightAction::SwordSweep && K->Action!=ESBKnightAction::Stomp &&
            K->Action!=ESBKnightAction::Bash && K->Action!=ESBKnightAction::ShieldCharge,
            TEXT("AI selected attack requiring destroyed armor"))) return;
        if (K->Action!=ESBKnightAction::BellWave || K->PatternElapsed<1.74f || !bSawBash) return;
        if (!Require(H->Health==100 && H->SelectedPart==ESBArmorPart::Body,TEXT("safe inner wave radius or broken-target cycle failed"))) return;
        Checkpoint(TEXT("after all breaks AI used shoulder check and wave; hugging the inner circle avoided wave damage; F skipped destroyed plates"));
        Next(15);return;
    case 81:
        if (K->Action!=ESBKnightAction::ShieldCharge || K->PatternElapsed<1.35f) return;
        if (!Require(H->Health==72 && !K->IsPunishWindow(),TEXT("stationary hero did not take one charge, or landed charge incorrectly exposed armor"))) return;
        Checkpoint(TEXT("standing in the lane took one 28-damage shield charge and granted no armor bonus"));
        Next(15);return;
    case 103:
        if (K->Health>0) return;
        if (!Require(K->bOathFinish,TEXT("lethal oath did not trigger its finisher"))) return;
        Checkpoint(TEXT("a lethal E triggered the delayed oath collapse"));
        Next(16);return;
    case 16:
    {
        bool Win=Run.Reloads%2==0;
        if (Win && G->Encounter==ESBEncounter::Altar)
        {
            Place(FVector(915,0,100),0);
            if (Run.Reloads==0 && !G->CanLightCandle() && FParse::Param(FCommandLine::Get(),TEXT("SBAuditGateView")) && G->OutcomeSeconds>=1.f && G->OutcomeSeconds-Dt<1.f)
                FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("QA/altar-candle.png"),false,false);
            if (G->CanLightCandle()) Tap(EKeys::E);
            return;
        }
        if (G->Encounter!=(Win?ESBEncounter::Victory:ESBEncounter::Defeat)) return;
        if (Win) ++Run.Victories; else ++Run.Defeats;
        ++Run.Reloads;Run.ReloadStarted=FPlatformTime::Seconds();
        Tap(EKeys::R);Next(17);return;
    }
    default: return; // OpenLevel will replace this actor.
    }
#endif
}
