D2RMM.copyFile(
  'hd', // <mod folder>\hd
  'hd', // <diablo 2 folder>\mods\<modname>\<modname>.mpq\data\hd
  true // overwrite any conflicts
);

// Back-to-back Smites crossfade into each other for 0.2 s, about half an attack at
// normal attack speeds, which blends away the step at the start of the animation.
// Shorten Smite -> Smite so each attack visibly steps in. Skill1 is the Paladin's S1
// mode, which only Smite uses.
const stateMachineFilename = 'hd\\character\\player\\paladin\\paladin_state_machine.json';
const stateMachine = D2RMM.readJson(stateMachineFilename);
const SKILL1 = 13; // stateId of State_Skill1
stateMachine.transitions.forEach((group) => {
  if (group.from === SKILL1) {
    group.settings.forEach((transition) => {
      if (transition.to === SKILL1) {
        transition.crossfadeSeconds = 0.05;
      }
    });
  }
});
D2RMM.writeJson(stateMachineFilename, stateMachine);
