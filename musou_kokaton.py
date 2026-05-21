import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
backgroundImg = ["fig/pg_bg.jpg","fig/pg_bg3.jpg","fig/pg_bg4.jpg","fig/yougan.png","fig/pg_bg5.jpg"] #1,2,3,4,5

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て,dstがどこにあるかを計算し,方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    state = "normal" 
    invincible_life = 0  # 無敵時間のタイマー

    delta = {  # 押下キーと移動量の辞書
        pg.K_w: (0, -1),
        pg.K_s: (0, +1),
        pg.K_a: (-1, 0),
        pg.K_d: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        self.base_image = pg.transform.flip(img0, True, False)
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.dire = (+1, 0)

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface, score: "Score"):
        """
        押下キーに応じてこうかとんを操作する
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])

        if key_lst[pg.K_RSHIFT] and score.value >= 100:# 無敵化の起動
            score.value -= 100
            self.state = "invincible"
            self.invincible_life = 500

        if self.state == "invincible": # 無敵時間の管理と描画
            if self.invincible_life > 0:
                self.invincible_life -= 1
                self.image = pg.transform.laplacian(self.image)
            else:
                self.state = "normal"
                self.image = self.base_image

        screen.blit(self.image, self.rect)


class Item(pg.sprite.Sprite):
    """
    回復アイテムに関するクラス
    """
    def __init__(self):
        super().__init__()
        self.image = pg.Surface((32, 32), pg.SRCALPHA)
        pg.draw.circle(self.image, (255, 80, 80), (16, 16), 16)
        pg.draw.circle(self.image, (255, 255, 255), (16, 16), 12)
        pg.draw.rect(self.image, (255, 80, 80), (13, 7, 6, 18))
        pg.draw.rect(self.image, (255, 80, 80), (7, 13, 18, 6))
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH + 40, random.randint(80, HEIGHT - 80)
        self.speed = random.randint(3, 6)

    def update(self):
        self.rect.move_ip(-self.speed, 0)
        if self.rect.right < 0:
            self.kill()
        

class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        if self.state == "active":
            yoko, tate = check_bound(self.rect)
            if not yoko: self.vx *= -1
            if not tate: self.vy *= -1

        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

        # if self.state == "active":
            # yoko, tate = check_bound(self.rect)
            # if not yoko: self.vx *= -1
            # if not tate: self.vy *= -1
        #     self.rect.move_ip(self.vx, self.vy)
        # screen.blit(self.image, self.rect)


class Fire(pg.sprite.Sprite):
    """
    炎の玉に関するクラス
    """
    imgs = pg.image.load(f"fig/fire.png")

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        炎の玉Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        self.image = pg.transform.rotozoom(self.imgs, 0, 0.8)
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active"

    def update(self):
        """
        火の玉を前進させ、完全に画面外に出たら消去する
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if (self.rect.right < 0 or            # 左側の画面外
            self.rect.left > 1100 or          # 右側の画面外
            self.rect.bottom < 0 or           # 上側の画面外
            self.rect.top > 650):             # 下側の画面外
            
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0=0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx)) + angle0  # ビームの角度を計算
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10
        #print(f"angle:{angle}")

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class NeoBeam(Beam):
    """
    複数方向に放つビームに関するクラス
    """
    def __init__(self, bird: Bird, num: int):
        self.bird = bird
        self.num = num

    def gen_beams(self, bird: Bird):
        """
        ビームを複数方向に放つ
        引数 bird：ビームを放つこうかとん
        """
        beams = []
        if self.num == 1:
            angles = [0]
        else:
            step = 100 // (self.num - 1)
            angles = list(range(-50, 51, step)) # ビームの角度を-50度から50度まで等間隔で生成
        for i in range(self.num):
            angle0 = angles[i]
            beams.append(Beam(bird, angle0))
        return beams

class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH + self.rect.width // 2, random.randint(50, HEIGHT - 150)
        self.vx, self.vy = -6, 0
        self.bound = random.randint(WIDTH // 2, WIDTH - 150)  # 停止位置
        self.state = "left"  # 左移動状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        self.hp = 1

    def update(self):
        """
        敵機を速度ベクトルself.vxに基づき移動（左移動）させる
        ランダムに決めた停止位置_boundまで左移動したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centerx < self.bound:
            self.vx = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Enemy4(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = pg.image.load(f"fig/enemy_4.png")
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(self.imgs, 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH + self.rect.width // 2, random.randint(50, HEIGHT - 150)
        self.vx, self.vy = -6, 0
        self.bound = random.randint(WIDTH // 2, WIDTH - 150)  # 停止位置
        self.state = "left"  # 左移動状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        self.hp = 1

    def update(self):
        """
        敵機を速度ベクトルself.vxに基づき移動（左移動）させる
        ランダムに決めた停止位置_boundまで左移動したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centerx < self.bound:
            self.vx = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Enemy4_1(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = pg.image.load(f"fig/moai.png")
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(self.imgs, 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.bottom = HEIGHT + 40  # 底面を少し下げる（以前の調整値）
        self.rect.left = WIDTH
        self.vx, self.vy = -6, 0
        self.bound = random.randint(WIDTH // 2, WIDTH - 150)  # 停止位置
        self.state = "left"  # 左移動状態or停止状態
        self.interval = random.randint(30, 300)  # 爆弾投下インターバル
        self.hp = 3

    def update(self):
        """
        敵機を速度ベクトルself.vxに基づき移動（左移動）させる
        ランダムに決めた停止位置_boundまで左移動したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centerx < self.bound:
            self.vx = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Enemy4_boss(pg.sprite.Sprite):
    """
    4ステージ目のボスに関するクラス
    """
    imgs = pg.image.load(f"fig/dragon.png")
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(self.imgs, 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH + self.rect.width // 2, HEIGHT // 2
        self.vx, self.vy = -6, 0
        self.bound = random.randint(WIDTH - 300, WIDTH - 150)  # 停止位置
        self.state = "left"  # 左移動状態or停止状態
        self.interval = random.randint(30, 100)  # 爆弾投下インターバル
        self.hp = 30

    def update(self):
        """
        敵機を速度ベクトルself.vxに基づき移動（左移動）させる
        ランダムに決めた停止位置_boundまで左移動したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centerx < self.bound:
            self.vx = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


def spawn_enemy(stage: int, tmr: int, emys: pg.sprite.Group):
    """
    ステージごとの条件に応じて敵機をスポーンさせる。
    現在はステージが上がるほど出現間隔を短くする。
    """
    interval = max(60, 200 - (stage - 1) * 20)
    if stage == 1:
        if tmr % interval == 0: # tmrがintervalの倍数のときに敵機をスポーンさせる
            emys.add(Enemy())
        # ここにステージごとのスポーン条件を追加していく
    # elif stage == 2:
        #     if tmr % 15
        #         emys.add(EnemyX())
    elif stage == 4:
        if tmr % interval == 0:
            emys.add(Enemy4())
        if tmr % 300 == 0:
            emys.add(Enemy4_1())
        if tmr % 1800 == 0 and tmr > 0:
            emys.add(Enemy4_boss())


class Full_beam:
    """
    複数方向に放つビームに関するクラス
    """
    def __init__(self, bird: Bird, num: int):
        self.bird = bird
        self.num = num

    def gen_beams(self, bird: Bird):
        """
        ビームを全方向（360度）に等間隔で放つ
        引数 bird：ビームを放つこうかとん
        """
        beams = []
        
        # 1本だけの場合は正面（0度）に撃つ
        if self.num == 1:
            angles = [0]
        else:
            # 360度を指定した本数(self.num)で等分割する
            step = 360 / self.num
            # 各ビームの角度を計算してリストにする（例: 4本なら [0.0, 90.0, 180.0, 270.0]）
            angles = [step * i for i in range(self.num)]
            
        for i in range(self.num):
            angle0 = angles[i]
            beams.append(Beam(bird, angle0))
            
        return beams


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 1000
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

class Life:
    """
    残機数に関するクラス
    """
    def __init__(self, num:int):
        """
        赤色のハートを生成する
        引数 num：初期残機数
        """
        self.num=num
        self.image=pg.Surface((40,40),pg.SRCALPHA)
        points = [(16*math.sin(t/100)**3 +20,
                -(13*math.cos(t/100)-5*math.cos(2*t/100)-2*math.cos(3*t/100)-math.cos(4*t/100)) +20
                ) for t in range(0, 628) ]
        pg.draw.polygon(self.image, (255,0,0), points)


    def update(self, screen: pg.Surface):
        """
        赤色のハートを画面右下に描写する
        """  
        x=(screen.get_width()-50)-20
        y=(screen.get_height()-50)-20
        for i in range(self.num):
            draw_x=x-(i*self.image.get_width())
            screen.blit(self.image,(draw_x,y))

def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_imgs = [pg.image.load(path).convert() for path in backgroundImg]
    score = Score()

    bird = Bird(3, (400, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    life = Life(3)
    items = pg.sprite.Group()

    stage = 1
    scroll = 2
    stage_clear = False
    stage_title_life = 0
    bg_x = 0

    player_skills = {
        1: False,  # 全方向ビーム
        2: False,  # スピードアップ（例）
        3: False,  # 攻撃力アップ（例）
        4: False,  # バリア（例）
        5: False,  # 運アップ（例）
    }

    current_choices = []
    full_beam_cooldown = 0

    pg.mixer.music.load("fig/進軍.mp3") 
    pg.mixer.music.play(loops=-1)

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0

            if stage_clear and event.type == pg.KEYDOWN and event.key in [pg.K_1, pg.K_2, pg.K_3]:
                # 押されたキーに応じて、選択肢リスト（current_choices）の何番目か特定する
                if event.key == pg.K_1:
                    chosen_index = 0
                elif event.key == pg.K_2:
                    chosen_index = 1
                elif event.key == pg.K_3:
                    chosen_index = 2
                
                # 実際に選ばれたスキルの本来の番号（1〜5）を取得する
                selected_skill_num = current_choices[chosen_index]
                
                # --- 変更点5：選ばれたスキルのフラグをTrueにする ---
                player_skills[selected_skill_num] = True
                
                # ※ デバッグ用：何番のスキルが適用されたかコンソールに出す
                print(f"Skill {selected_skill_num} Activated!")
                
                # 次のステージへ行くための共通処理
                life.num = min(life.num + 1, 5)
                score.value += 50
                stage += 1
                stage_clear = False
                stage_title_life = 60
                bird.rect.center = (900, 400)
                
                emys.empty()
                bombs.empty()
                beams.empty()
                items.empty()
                tmr = 0
                bg_x = 0
                continue

            if stage_clear:
                continue

            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if event.mod & pg.KMOD_LSHIFT: #発動条件：左Shiftキーを押下しながらスペースキー
                    beams.add(*NeoBeam(bird, 5).gen_beams(bird))  # Shift+スペースで複数方向にビームを放つ
                else:
                    beams.add(Beam(bird))  # スペースキーでビームを放つ
            
            if event.type == pg.KEYDOWN and event.key == pg.K_r:
                # スキルを所持していて、かつクールダウンが0の場合のみ発動
                if player_skills[1] and full_beam_cooldown == 0:
                    beams.add(*Full_beam(bird, 8).gen_beams(bird))
                    full_beam_cooldown = 300

        bg_img = bg_imgs[(stage - 1) % len(bg_imgs)]
        bg_x = (bg_x - scroll) % WIDTH
        screen.blit(bg_img, (bg_x - WIDTH, 0))
        screen.blit(bg_img, (bg_x, 0))

        if stage_clear:
            overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            
            font = pg.font.Font(None, 54)
            font_sub = pg.font.Font(None, 40)
            
            # --- 変更点1：テキスト表示の変更 ---
            lines = [
                f"STAGE {stage} CLEAR",
                "Select 1 Skill to Upgrade!",
            ]
            for i, text in enumerate(lines):
                img = font.render(text, True, (255, 255, 255))
                rect = img.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150 + i * 50))
                screen.blit(img, rect)
            
            skill_names = {
                1: "Full Beam (Omnidirectional)",
                2: "Speed Up (Coming Soon)",
                3: "Max HP Up (Coming Soon)",
                4: "Shield (Coming Soon)",
                5: "Lucky (Coming Soon)",
            }
            for i, skill_num in enumerate(current_choices):
                # i は 0, 1, 2 なので、キーの表示は 1, 2, 3 になる
                skill_text = f"[ {i + 1} ]  {skill_names[skill_num]}"
                
                # スキル1だけ完成しているので、1が含まれる選択肢を黄色にする例
                color = (255, 215, 0) if skill_num == 1 else (150, 150, 150)
                
                img = font_sub.render(skill_text, True, color)
                rect = img.get_rect(center=(WIDTH // 2, HEIGHT // 2 + i * 60))
                screen.blit(img, rect)

            pg.display.update()
            clock.tick(30)
            continue

        if stage_title_life > 0:
            font = pg.font.Font(None, 48)
            img = font.render(f"STAGE {stage}", True, (255, 255, 255))
            rect = img.get_rect(center=(WIDTH // 2, 50))
            screen.blit(img, rect)
            stage_title_life -= 1
        

        spawn_enemy(stage, tmr, emys)
        if tmr%260 == 0:
            items.add(Item())

        if bird.rect.left <= 0:
            stage_clear = True

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                
                # 2. そのタイミングの中で、ボスか雑魚敵かを分ける
                if isinstance(emy, Enemy4_boss):
                    # 4面ボスの場合は Fire だけを1個投下
                    print("★ボスがFireを撃った瞬間！")
                    bombs.add(Fire(emy, bird)) 
                else:
                    # モアイなどの雑魚敵の場合は Bomb だけを1個投下
                    bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.spritecollide(bird, emys, False):
            emy.hp -= 1
            if emy.hp <= 0:
                emys.remove(emy)
                exps.add(Explosion(emy, 100))
                score.value += 10
            life.num -= 1
            bird.change_img(8, screen)
            score.update(screen)
            life.update(screen)
            pg.display.update()
            if life.num < 1:
                game_over_font = pg.font.Font(None, 100)
                game_over_img = game_over_font.render("GAME OVER", True, (255, 255, 255))
                game_over_rect = game_over_img.get_rect(center=(WIDTH // 2, HEIGHT // 2))
                screen.blit(game_over_img, game_over_rect)
                pg.display.update()
                time.sleep(2)
                return

        for obj in emys:
            if isinstance(obj, Enemy4_boss):
                continue
            obj.rect.x -= scroll
        for obj in bombs:
            obj.rect.x -= scroll
        for obj in beams:
            obj.rect.x -= scroll
        for obj in exps:
            obj.rect.x -= scroll
        for obj in items:
            obj.rect.x -= scroll

        for item in pg.sprite.spritecollide(bird, items, True):
            life.num = min(life.num + 1, 5)
            score.value += 20

        for emy in pg.sprite.groupcollide(emys, beams, False, True).keys():  # ビームと衝突した敵機リスト
            emy.hp -= 1
            if emy.hp <= 0:
                emys.remove(emy)
                exps.add(Explosion(emy, 100))  # 爆発エフェクト
                score.value += 10  # 10点アップ
                bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ
        

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            if bird.state == "invincible":
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1  # 1点アップ
            else:
                if bomb.state == "active": 
                    life.num-=1 #　衝突したらライフが一つ減る
                    bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                    score.update(screen)
                    life.update(screen)
                    pg.display.update()
                    if life.num<1:
                        time.sleep(2)
                        return
                    
        if emy.hp <= 0:
            # 敵が倒されたとき、それがボス（Enemy4_boss）だった場合
            if isinstance(emy, Enemy4_boss):
                stage_clear = True  # ステージクリアフラグをONにする
                current_choices = random.sample([1, 2, 3, 4, 5], 3)

        if player_skills[1] and full_beam_cooldown > 0:
            font_cd = pg.font.Font(None, 30)
            # フレーム数を秒数に変換（60で割る）して、小数点第1位まで表示
            cd_sec = full_beam_cooldown / 60
            img_cd = font_cd.render(f"SKILL R CD: {cd_sec:.1f}s", True, (255, 0, 0))
            screen.blit(img_cd, (20, 100))

        if full_beam_cooldown > 0:
            full_beam_cooldown -= 1
        
        # if tmr % 1800 == 0 and tmr > 0:
        #     stage_clear = True

        bird.update(key_lst, screen, score)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        items.update()
        items.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        life.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    pg.mixer.init()
    main()
    pg.quit()
    sys.exit()