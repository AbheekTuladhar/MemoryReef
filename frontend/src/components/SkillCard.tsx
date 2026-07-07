import { Skill } from "../types";

export function SkillCard({ skill }: { skill: Skill }) {
  return (
    <article className="skillCard">
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
