// A utility function designed to group an array of skills strictly by their source natively mapping pure arrays without server queries avoiding UI loops.

export const SkillGrouping = (skills: any[]) => {
    return skills.reduce((groups, skill) => {
        const src = skill.source || 'built-in';
        if (!groups[src]) groups[src] = [];
        groups[src].push(skill);
        return groups;
    }, {} as Record<string, any[]>);
};

export default SkillGrouping;
