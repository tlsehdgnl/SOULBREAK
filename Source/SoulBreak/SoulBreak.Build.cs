// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class SoulBreak : ModuleRules
{
	public SoulBreak(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"PhysicsCore",
			"ProceduralMeshComponent",
			"SlateCore",
			"NavigationSystem",
			"GameplayTasks",
			"AudioMixer",
			"Json",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.Add("RenderCore");

		PublicIncludePaths.AddRange(new string[] {
			"SoulBreak",
			"SoulBreak/Variant_Platforming",
			"SoulBreak/Variant_Platforming/Animation",
			"SoulBreak/Variant_Combat",
			"SoulBreak/Variant_Combat/AI",
			"SoulBreak/Variant_Combat/Animation",
			"SoulBreak/Variant_Combat/Gameplay",
			"SoulBreak/Variant_Combat/Interfaces",
			"SoulBreak/Variant_Combat/UI",
			"SoulBreak/Variant_SideScrolling",
			"SoulBreak/Variant_SideScrolling/AI",
			"SoulBreak/Variant_SideScrolling/Gameplay",
			"SoulBreak/Variant_SideScrolling/Interfaces",
			"SoulBreak/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
