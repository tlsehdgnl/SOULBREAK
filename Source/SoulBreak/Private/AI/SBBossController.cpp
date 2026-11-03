#include "AI/SBBossController.h"
#include "Boss/SBKnight.h"
#include "Player/SBHero.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BehaviorTreeComponent.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Bool.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Object.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Int.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Float.h"
#include "BehaviorTree/Composites/BTComposite_Selector.h"

USBSelectAttackTask::USBSelectAttackTask()
{
    NodeName=TEXT("Read arm and phase, select and resolve an attack");
    INIT_TASK_NODE_NOTIFY_FLAGS();
}
EBTNodeResult::Type USBSelectAttackTask::ExecuteTask(UBehaviorTreeComponent& Owner,uint8*)
{
    return Owner.GetAIOwner() && Cast<ASBKnight>(Owner.GetAIOwner()->GetPawn()) ? EBTNodeResult::InProgress:EBTNodeResult::Failed;
}
void USBSelectAttackTask::TickTask(UBehaviorTreeComponent& Owner,uint8*,float Dt)
{
    auto* K=Cast<ASBKnight>(Owner.GetAIOwner()->GetPawn());
    if (K && K->bEncounterActive) K->Think(Dt);
}
EBTNodeResult::Type USBSelectAttackTask::AbortTask(UBehaviorTreeComponent& Owner,uint8*)
{
    if (auto* AI=Owner.GetAIOwner())
    {
        AI->StopMovement();
        if (auto* K=Cast<ASBKnight>(AI->GetPawn())) K->StopEncounter();
    }
    return EBTNodeResult::Aborted;
}
void USBSelectAttackTask::ConfigureDuelTree(UBehaviorTree* Tree,UBlackboardData* BB)
{
    if (!Tree || !BB) return;
    BB->Keys.Reset();
    auto Key=[&](FName Name,UBlackboardKeyType* Type) {
        FBlackboardEntry E; E.EntryName=Name; E.KeyType=Type; BB->Keys.Add(E);
    };
    Key(TEXT("Target"),NewObject<UBlackboardKeyType_Object>(BB));
    Key(TEXT("Phase"),NewObject<UBlackboardKeyType_Int>(BB));
    Key(TEXT("ArmIntact"),NewObject<UBlackboardKeyType_Bool>(BB));
    Key(TEXT("Busy"),NewObject<UBlackboardKeyType_Bool>(BB));
    Key(TEXT("Distance"),NewObject<UBlackboardKeyType_Float>(BB));
    Tree->BlackboardAsset=BB;
    Tree->RootNode=NewObject<UBTComposite_Selector>(Tree);
    FBTCompositeChild Child; Child.ChildTask=NewObject<USBSelectAttackTask>(Tree->RootNode);
    Tree->RootNode->Children.Add(Child);
}
void ASBBossController::BeginDuel(ASBKnight& Knight)
{
    // Build a native tree when the designer has not assigned an authored BT. Both share
    // the same state owner and there are no delayed attack callbacks to outlive a restart.
    DuelTree=LoadObject<UBehaviorTree>(nullptr,TEXT("/Game/SoulBreak/AI/BT_Knight.BT_Knight"),nullptr,LOAD_NoWarn);
    if (!DuelTree || !DuelTree->RootNode || DuelTree->RootNode->Children.IsEmpty())
    {
        DuelTree=NewObject<UBehaviorTree>(this);
        auto* BB=NewObject<UBlackboardData>(DuelTree);
        USBSelectAttackTask::ConfigureDuelTree(DuelTree,BB);
    }
    RunBehaviorTree(DuelTree); Sync(Knight);
}
void ASBBossController::Sync(const ASBKnight& K)
{
    UBlackboardComponent* BB=GetBlackboardComponent();
    if (!BB || !K.GetHero()) return;
    BB->SetValueAsObject(TEXT("Target"),K.GetHero());
    BB->SetValueAsFloat(TEXT("Distance"),FVector::Dist2D(K.GetActorLocation(),K.GetHero()->GetActorLocation()));
    BB->SetValueAsInt(TEXT("Phase"),K.Phase);
    BB->SetValueAsBool(TEXT("ArmIntact"),!K.bArmBroken);
    BB->SetValueAsBool(TEXT("Busy"),K.Action!=ESBKnightAction::Chase && K.Action!=ESBKnightAction::Idle);
}
