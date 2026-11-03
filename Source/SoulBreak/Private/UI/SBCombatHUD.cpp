#include "UI/SBCombatHUD.h"
#include "Core/SBGameMode.h"
#include "Combat/SBTrainingDummy.h"
#include "Player/SBHero.h"
#include "Boss/SBKnight.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "CanvasItem.h"

namespace
{
const FLinearColor Ink(.013f,.019f,.024f,.87f);
const FLinearColor Paper(.94f,.91f,.80f,1);
const FLinearColor Gold(.88f,.65f,.30f,1);
const FLinearColor Muted(.69f,.75f,.74f,1);
const FLinearColor Aqua(.24f,.79f,.76f,1);
const FLinearColor Blood(.79f,.18f,.16f,1);
}

void ASBCombatHUD::Box(float X,float Y,float Width,float Height,FLinearColor Color)
{
    DrawRect(Color, X*Unit,Y*Unit,Width*Unit,Height*Unit);
}
void ASBCombatHUD::Line(float X,float Y,float X2,float Y2,FLinearColor Color,float Weight)
{
    DrawLine(X*Unit,Y*Unit,X2*Unit,Y2*Unit,Color,Weight*Unit);
}
void ASBCombatHUD::Label(const FString& Text,float X,float Y,float Size,FLinearColor Color,bool Center)
{
    UFont* Font = GEngine->GetLargeFont();
    if (!Font || Text.IsEmpty()) return;
    const float Scale = Unit * Size / FMath::Max(1.f,static_cast<float>(Font->GetMaxCharHeight()));
    FCanvasTextItem Item(FVector2D(X*Unit,Y*Unit),FText::FromString(Text),Font,Color);
    Item.Scale = FVector2D(Scale);
    Item.bCentreX = Center;
    Item.EnableShadow(FLinearColor(0,0,0,.9f),FVector2D(Unit,Unit));
    Canvas->DrawItem(Item);
}
void ASBCombatHUD::Diamond(float X,float Y,float R,FLinearColor Color)
{
    Line(X-R,Y,X,Y-R,Color); Line(X,Y-R,X+R,Y,Color);
    Line(X+R,Y,X,Y+R,Color); Line(X,Y+R,X-R,Y,Color);
}
void ASBCombatHUD::Meter(float X,float Y,float Width,float Height,float Value,float Max,FLinearColor Color)
{
    Box(X-1,Y-1,Width+2,Height+2,FLinearColor(.025f,.028f,.034f,.94f));
    Box(X,Y,Width,Height,FLinearColor(.13f,.13f,.14f,.98f));
    const float Filled = Width*FMath::Clamp(Value/Max,0.f,1.f);
    Box(X,Y,Filled,Height,Color);
    if (Filled > 2) Box(X+Filled-2,Y,2,Height,Paper);
}
void ASBCombatHUD::DrawHUD()
{
    Super::DrawHUD();
    if (!Canvas) return;
    const ASBGameMode* Game = GetWorld()->GetAuthGameMode<ASBGameMode>();
    if (!Game || !Game->Hero || !Game->Knight) return;
    Unit = FMath::Max(.2f,FMath::Min(Canvas->ClipX/1280.f,Canvas->ClipY/720.f));
    W = Canvas->ClipX/Unit; H = Canvas->ClipY/Unit;
    if (Game->bHelpOpen) { Guide(); return; }
    if (Game->Encounter == ESBEncounter::Victory || Game->Encounter == ESBEncounter::Defeat)
    {
        Result(*Game); return;
    }
    Vitals(*Game);
    if (Game->Encounter == ESBEncounter::Fighting) Encounter(*Game);
    else
    {
        FVector2D Pt;
        if (Game->Dummy && PlayerOwner->ProjectWorldLocationToScreen(Game->Dummy->GetActorLocation()+FVector(0,0,204),Pt))
        {
            float X=Pt.X/Unit,Y=Pt.Y/Unit;
            if (X>50 && X<W-50 && Y>32 && Y<H-120)
            {
                Box(X-56,Y-3,112,32,Ink);
                Label(FString::Printf(TEXT("훈련 표적   %d"),FMath::CeilToInt(Game->Dummy->Health)),X,Y,15,Paper,true);
                Meter(X-43,Y+21,86,3,Game->Dummy->Health,100,Gold);
            }
        }
        Box(32,32,282,112,Ink); Box(32,32,3,112,Gold);
        Label(TEXT("S O U L   B R E A K"),51,44,17,Gold);
        Label(TEXT("잿빛 대성당"),50,66,33,Paper);
        Label(TEXT("빛의 선을 넘어 기사에게 도전하세요"),51,112,16,Muted);
        Box(W-372,H-120,340,92,Ink);
        Label(TEXT("W A S D   이동     마우스   시점"),W-355,H-109,17,Paper);
        Label(TEXT("좌클릭   베기     우클릭   패링"),W-355,H-83,17,Paper);
        Label(TEXT("Space   회피     Tab   고정     F1   조작"),W-355,H-56,16,Gold);
    }
}
void ASBCombatHUD::Vitals(const ASBGameMode& Game)
{
    const float Y = H-95;
    Box(32,Y,265,65,Ink);
    Diamond(55,Y+32,14,Gold); Diamond(55,Y+32,8,Aqua); Line(55,Y+20,55,Y+44,Gold);
    Label(TEXT("순례자"),81,Y+4,17,Paper);
    Label(FString::Printf(TEXT("%d / 100"),FMath::CeilToInt(Game.Hero->Health)),215,Y+5,14,Muted);
    Meter(81,Y+30,199,10,Game.Hero->Health,100,Blood);
    Meter(81,Y+47,199,5,Game.Hero->Stamina,100,Aqua);
}
void ASBCombatHUD::Encounter(const ASBGameMode& Game)
{
    const ASBKnight& Boss = *Game.Knight;
    const float C = W*.5f;
    Box(C-264,20,528,78,Ink);
    Label(Boss.Phase == 1 ? TEXT("I    /    칼날의 맹세") : TEXT("II    /    무너진 서약"),C,25,14,Gold,true);
    Label(TEXT("잿빛 성당의 기사"),C,42,24,Paper,true);
    Meter(C-246,75,492,8,Boss.Health,400,Blood);
    Box(W-222,32,190,62,Ink);
    Label(Boss.bArmBroken ? TEXT("오른팔   ·   파괴됨") : TEXT("오른팔   ·   검 갑주"),W-209,39,17,Boss.bArmBroken ? Gold : Paper);
    Meter(W-209,70,161,6,Boss.ArmHealth,90,Gold);
    if (Boss.bArmBroken && !bSawBreak)
    {
        bSawBreak=true; ArmNoticeUntil=GetWorld()->GetTimeSeconds()+2.3f;
    }
    if (GetWorld()->GetTimeSeconds()<ArmNoticeUntil)
    {
        Box(C-147,H*.26f,294,58,Ink);
        Label(TEXT("A R M O R   B R O K E N"),C,H*.26f+5,15,Gold,true);
        Label(TEXT("검을 든 오른팔 파괴"),C,H*.26f+25,21,Paper,true);
    }
    if (Boss.TelegraphDuration > 0 && Boss.PatternElapsed < Boss.TelegraphDuration && !Boss.PatternLabel.IsEmpty())
    {
        Box(C-106,H-100,212,47,Ink);
        Label(Boss.PatternLabel,C,H-95,19,Paper,true);
        Meter(C-90,H-64,180,4,Boss.PatternElapsed,Boss.TelegraphDuration,Gold);
    }
    if (Game.Hero->bLockedOn)
    {
        FVector2D Pt;
        if (PlayerOwner->ProjectWorldLocationToScreen(Boss.GetActorLocation()+FVector(0,0,32),Pt))
            Diamond(Pt.X/Unit,Pt.Y/Unit,7,Paper);
    }
    if (Game.Hero->bOathReady)
    {
        Box(32,H-134,215,31,Ink);
        Diamond(48,H-119,6,Aqua);
        Label(TEXT("E   서약 절단 준비"),65,H-132,19,Aqua);
    }
    if (Game.Hero->ParryPulse > 0) Label(TEXT("완벽한 패링"),C,H*.60f,24,Aqua,true);
    if (Game.Hero->HitPulse > 0)
    {
        const FLinearColor Red(.65f,.03f,.02f,.52f*Game.Hero->HitPulse);
        Box(0,0,W,5,Red); Box(0,H-5,W,5,Red);
    }
    Label(TEXT("F1   조작"),W-102,H-52,15,Muted);
}
void ASBCombatHUD::Guide()
{
    Box(0,0,W,H,FLinearColor(.008f,.013f,.019f,.85f));
    const float X=W*.5f-204, Y=H*.5f-198;
    Line(X,Y,X+408,Y,Gold);
    Label(TEXT("S O U L   B R E A K     /     P A U S E"),X,Y+15,16,Gold);
    Label(TEXT("순례자의 전투 수첩"),X,Y+46,34,Paper);
    const TCHAR* Keys[]={TEXT("W A S D  /  마우스"),TEXT("Shift  /  Space"),TEXT("좌클릭  ×  2"),TEXT("우클릭"),TEXT("Tab  /  E")};
    const TCHAR* Acts[]={TEXT("이동  /  시점"),TEXT("달리기  /  회피"),TEXT("검 베기  /  연계 공격"),TEXT("패링  ·  검이 닿기 직전에"),TEXT("기사 고정  /  패링 후 서약 절단")};
    for (int32 I=0;I<5;++I)
    {
        const float Row=Y+109+I*34;
        Label(Keys[I],X,Row,18,Gold); Label(Acts[I],X+180,Row,18,Paper);
    }
    Label(TEXT("기사의 오른쪽으로 돌아 검을 든 팔을 노리세요."),X,Y+292,18,Muted);
    Line(X,Y+338,X+408,Y+338,Gold);
    Label(TEXT("Esc / F1   계속      R   재도전      Q   종료"),X,Y+356,17,Paper);
}
void ASBCombatHUD::Result(const ASBGameMode& Game)
{
    const bool Win = Game.Encounter==ESBEncounter::Victory;
    const float Fade=FMath::Clamp(Game.OutcomeSeconds*1.4f,0.f,1.f);
    Box(0,0,W,H,FLinearColor(.006f,.01f,.015f,Fade*.6f));
    if (Fade<.25f) return;
    const float C=W*.5f,Y=H*.35f;
    Box(C-235,Y-22,470,229,Ink);
    Line(C-210,Y-1,C-18,Y-1,Gold); Diamond(C,Y-1,7,Gold); Line(C+18,Y-1,C+210,Y-1,Gold);
    Label(Win ? TEXT("O A T H   S E V E R E D") : TEXT("P I L G R I M   F A L L E N"),C,Y+15,17,Gold,true);
    Label(Win ? TEXT("기사의 맹세를 끊었다") : TEXT("순례자가 쓰러졌다"),C,Y+45,36,Paper,true);
    const int32 Sec=FMath::FloorToInt(Game.FightSeconds);
    Label(FString::Printf(TEXT("%02d:%02d     /     오른팔 %s"),Sec/60,Sec%60,Game.Knight->bArmBroken ? TEXT("파괴") : TEXT("온전")),C,Y+105,17,Muted,true);
    Label(TEXT("R   다시 도전      Q   게임 종료"),C,Y+156,20,Gold,true);
}
