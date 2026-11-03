#pragma once
#include "AIController.h"
#include "BehaviorTree/BTTaskNode.h"
#include "SBBossController.generated.h"

class UBehaviorTree;
class UBlackboardData;
class ASBKnight;

UCLASS()
class SOULBREAK_API USBSelectAttackTask : public UBTTaskNode
{
    GENERATED_BODY()
public:
    USBSelectAttackTask();
    UFUNCTION(BlueprintCallable, Category="Soul Break|AI") static void ConfigureDuelTree(UBehaviorTree* Tree,UBlackboardData* Blackboard);
    virtual EBTNodeResult::Type ExecuteTask(UBehaviorTreeComponent& Owner,uint8* Memory) override;
    virtual EBTNodeResult::Type AbortTask(UBehaviorTreeComponent& Owner,uint8* Memory) override;
    virtual void TickTask(UBehaviorTreeComponent& Owner,uint8* Memory,float Dt) override;
};
UCLASS()
class SOULBREAK_API ASBBossController : public AAIController
{
    GENERATED_BODY()
public:
    void BeginDuel(ASBKnight& Knight);
    void Sync(const ASBKnight& Knight);
private:
    UPROPERTY() TObjectPtr<UBehaviorTree> DuelTree;
};
