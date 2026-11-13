# 훈련 표적과 제단화

훈련 표적의 기둥과 방패에는 Rob Tuytel이 촬영한 Poly Haven의 목재와 가죽 색상·노멀·거칠기 맵을 사용했다. 모델, 끈 감기, 바느질, 흠집, 접합부와 금속 장식은 이 프로젝트에서 제작했다. [Rough Wood](https://polyhaven.com/a/rough_wood) · [Brown Leather](https://polyhaven.com/a/brown_leather) · [CC0 라이선스](https://polyhaven.com/license)

표적을 다시 제작할 때 Blender에서 `build_pell.py`를 실행하고, NumPy가 설치된 Python으로 `Tools/Art/build_sound.py Saved/SBArmory`를 실행한다. Unreal Editor Python에서 `Tools/Editor/import_armory.py`를 실행하면 두 메시, 표면과 전투 효과음 네 개를 임포트한다. 완성된 프로젝트에는 임포트된 에셋이 포함되어 있다.

기사와 순례자의 갑주에는 산화한 강철의 명도와 거칠기, 의복에는 모직·린넨의 결을 입혔다. 색상과 금속성은 각 장비의 팔레트에 맞추고 메시의 바인드 포즈를 기준으로 옷자락과 부츠의 먼지 농도를 정했다. 금속과 가죽은 Rob Tuytel, 두 직물의 사진은 colormass, 직물 가공은 Rico Cilliers가 제공했다. [Metal Plate 02](https://polyhaven.com/a/metal_plate_02) · [Poly Wool Herringbone](https://polyhaven.com/a/poly_wool_herringbone) · [Rough Linen](https://polyhaven.com/a/rough_linen)

캐릭터 에셋과 스켈레톤을 다시 임포트한 뒤 `Tools/Art/build_armor_surfaces.py`를 실행하고, 에디터에서 `Tools/Editor/import_armor_surfaces.py`를 실행한다. 첫 실행에서 소스 스캔을 받아 SHA-256으로 확인하고, 이후에는 저장된 스캔으로 재생성한다.

제단의 목조 부조 이미지는 내장 imagegen으로 만든 원본 `SeveredOath.png`이다. 생성 프롬프트는 다음과 같다.

> Create a production game environmental texture, full bleed portrait 2:3, an orthographic front-facing conservation photograph of one physically existing antique gilded and carved oak altarpiece relief from a ruined late-medieval Gothic cathedral. Original subject: a solitary crowned knight kneels head slightly bowed in profile at center, putting a sword point down into earth; his damaged sword-arm pauldron lies below the point. The large central knight and sword silhouette reads from across the nave. Narrow outer perimeter of worn leaf tracery. Dramatic composition in aged dark oiled walnut, dull antique brass-gold leaf and deep oxidized umber, small areas of dried red-brown bole under flaked gold. Subtle fine cracks, tool marks, tarnish, polygonally carved relief folds, woodgrain peeking through gold, realistically aged, old museum art object, quietly somber. Diffuse even museum documentation light, gentle occlusion in crevices, no hard directional shadow, NO scene, NO outside frame wall, no perspective, no unreal glow, no blue glass, no bright white highlights, no text, no watermark, no graphic design. Entire image filled by artifact, no margins, depiction itself is physically carved wood sculpture, not a photograph of a living person. Dense crafted textures, readable medium values.
