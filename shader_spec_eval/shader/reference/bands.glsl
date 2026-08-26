void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    float x = fragCoord.x / iResolution.x;
    float v = floor(min(x, 0.9999) * 5.0) / 4.0;
    fragColor = vec4(vec3(v), 1.0);
}
