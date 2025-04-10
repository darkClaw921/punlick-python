import math
progress_bars={
    'progress_bar_id':{
        'processed':45,
        'text':''
    }
}
items=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40]
max_percent_is_step=90
now_percent_step=progress_bars['progress_bar_id']['processed']
max_percent_step=max_percent_is_step - now_percent_step
#
# Обработка по 17 элементов за итерацию
batch_size = 17
print(math.ceil(len(items)/batch_size))
percent_step=round(max_percent_step/math.ceil(len(items)/batch_size),1)
print(percent_step)