void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = fragCoord / iResolution.y;
    float aspect = iResolution.x / iResolution.y;
    bool xok = abs(p.x - 0.5 * aspect) <= 0.25;
    bool yok = p.y >= 0.59 && p.y <= 0.77;
    fragColor = vec4((xok && yok) ? vec3(0.96, 0.08, 0.86) : vec3(0.012), 1.0);
}
