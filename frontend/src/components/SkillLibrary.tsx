import { Skill } from "../types";
import { SkillCard } from "./SkillCard";

export function SkillLibrary({ skills }: { skills: Skill[] }) {
  return (
    <section className="panel">
      <h2>Skill Library</h2>
      {skills.length === 0 ? (
        <p>No skills saved yet.</p>
      ) : (
        <div className="skillList">
          {skills.map((skill) => (
            <SkillCard key={skill.skill_id} skill={skill} />
          ))}
        </div>
      )}
    </section>
  );
}
