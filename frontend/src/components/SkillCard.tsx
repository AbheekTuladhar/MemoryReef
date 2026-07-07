import { Skill } from "../types";

export function SkillCard({ skill, isNew }: { skill: Skill; isNew?: boolean }) {
  return (
    <article className={`skillCard${isNew ? " pearl" : ""}`}>
      {isNew && <span className="pearlBadge">New pearl</span>}
      <div className="skillTitle">
        <h3>{skill.name}</h3>
        <span>{skill.status}</span>
      </div>
      <p>{skill.description}</p>
      <div className="tagRow">
        {skill.tags.map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
      <p className="subtle">Used {skill.usage_count} times</p>
    </article>
  );
}
