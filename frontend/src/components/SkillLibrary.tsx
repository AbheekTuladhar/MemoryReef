import { Skill } from "../types";
import { SkillCard } from "./SkillCard";

export function SkillLibrary({ skills, newSkillId }: { skills: Skill[]; newSkillId?: string }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <h2>The Reef</h2>
          <p>Saved pearls Dory can reach for on the next dive.</p>
        </div>
        <span className="reefCount">{skills.length} saved</span>
      </div>
      {skills.length === 0 ? (
        <p className="subtle">No pearls yet. Reflect, verify, and save to grow the reef.</p>
      ) : (
        <div className="skillList">
          {skills.map((skill) => (
            <SkillCard key={skill.skill_id} skill={skill} isNew={skill.skill_id === newSkillId} />
          ))}
        </div>
      )}
    </section>
  );
}
