void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec2 c = floor(uv * 8.0);
    float check = mod(c.x + c.y, 2.0);
    vec3 col = mix(vec3(0.02, 0.03, 0.02), vec3(0.15, 0.95, 0.25), check);
    fragColor = vec4(col, 1.0);
}
