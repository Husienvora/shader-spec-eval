void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    float r = length(p);
    float angular = 0.55 + 0.45 * abs(sin(3.0 * atan(p.y, p.x) + iTime));
    float fade = exp(-5.0 * r * r);
    fragColor = vec4(vec3(0.03, 0.65, 0.88) * angular * fade, 1.0);
}
